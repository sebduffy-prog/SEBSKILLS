#!/usr/bin/env python3
"""Dependency-light semantic response cache.

An embedding-similarity cache you can drop in front of any LLM call: near-duplicate
prompts reuse a stored answer and skip inference. No vector DB required — it keeps
vectors in a numpy matrix in-process (fine up to ~50k entries) with optional
JSON persistence. Swap the embed function for OpenAI/SBERT/Cohere as needed.

Usage:
    from semantic_cache import SemanticCache
    cache = SemanticCache(embed_fn=my_embed, threshold=0.85)
    hit = cache.get("What is the capital of France?")
    if hit is None:
        answer = call_llm(prompt)          # miss -> pay for inference
        cache.set(prompt, answer)
    else:
        answer = hit                       # hit  -> free

Run `python semantic_cache.py` for a self-test using a toy hash embedder.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np

# Cosine-similarity floor for a hit. 1.0 = identical direction. Tune per embedder:
# OpenAI/SBERT paraphrases usually land 0.90-0.99; start strict and loosen.
DEFAULT_THRESHOLD = 0.85


@dataclass
class _Entry:
    prompt: str
    response: str
    created_at: float
    hits: int = 0


@dataclass
class SemanticCache:
    embed_fn: Callable[[str], "np.ndarray"]
    threshold: float = DEFAULT_THRESHOLD
    ttl_seconds: Optional[float] = None  # None = never expire
    _vectors: Optional["np.ndarray"] = field(default=None, repr=False)
    _entries: list = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not 0.0 < self.threshold <= 1.0:
            raise ValueError(f"threshold must be in (0, 1], got {self.threshold}")

    @staticmethod
    def _unit(vec: "np.ndarray") -> "np.ndarray":
        vec = np.asarray(vec, dtype=np.float32).ravel()
        norm = float(np.linalg.norm(vec))
        if norm == 0.0:
            raise ValueError("embedding has zero norm; cannot normalize")
        return vec / norm

    def _fresh(self, entry: _Entry) -> bool:
        if self.ttl_seconds is None:
            return True
        return (time.time() - entry.created_at) <= self.ttl_seconds

    def get(self, prompt: str) -> Optional[str]:
        """Return a cached response for a semantically-near prompt, else None."""
        if self._vectors is None or len(self._entries) == 0:
            return None
        query = self._unit(self.embed_fn(prompt))
        sims = self._vectors @ query  # rows are unit vectors -> dot == cosine
        best = int(np.argmax(sims))
        if float(sims[best]) < self.threshold:
            return None
        entry = self._entries[best]
        if not self._fresh(entry):
            return None
        entry.hits += 1
        return entry.response

    def set(self, prompt: str, response: str) -> None:
        """Store a new prompt/response pair."""
        vec = self._unit(self.embed_fn(prompt)).reshape(1, -1)
        self._vectors = vec if self._vectors is None else np.vstack([self._vectors, vec])
        self._entries.append(_Entry(prompt, response, time.time()))

    def stats(self) -> dict:
        total_hits = sum(e.hits for e in self._entries)
        return {"entries": len(self._entries), "total_hits": total_hits}

    def save(self, path: str) -> None:
        payload = {
            "threshold": self.threshold,
            "ttl_seconds": self.ttl_seconds,
            "entries": [e.__dict__ for e in self._entries],
            "vectors": self._vectors.tolist() if self._vectors is not None else [],
        }
        Path(path).write_text(json.dumps(payload))

    def load(self, path: str) -> None:
        payload = json.loads(Path(path).read_text())
        self.threshold = payload["threshold"]
        self.ttl_seconds = payload["ttl_seconds"]
        self._entries = [_Entry(**e) for e in payload["entries"]]
        vecs = payload["vectors"]
        self._vectors = np.asarray(vecs, dtype=np.float32) if vecs else None


def _toy_embed(text: str, dim: int = 64) -> "np.ndarray":
    """Deterministic bag-of-words hash embedder — for self-test only, NOT production."""
    vec = np.zeros(dim, dtype=np.float32)
    for tok in text.lower().split():
        vec[hash(tok) % dim] += 1.0
    if float(np.linalg.norm(vec)) == 0.0:
        vec[0] = 1.0
    return vec


if __name__ == "__main__":
    c = SemanticCache(embed_fn=_toy_embed, threshold=0.6)
    assert c.get("capital of France") is None, "empty cache must miss"
    c.set("what is the capital of France", "Paris")
    assert c.get("what is the capital of France") == "Paris", "exact repeat must hit"
    assert c.get("the capital of France what is") == "Paris", "reordered near-dup must hit"
    assert c.get("who won the 1998 world cup") is None, "unrelated must miss"
    print("self-test OK", c.stats())
