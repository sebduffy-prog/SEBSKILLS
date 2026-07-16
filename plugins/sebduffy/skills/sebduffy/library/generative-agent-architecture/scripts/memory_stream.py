"""Minimal, faithful port of the Stanford "Generative Agents" memory stream.

Grounded on joonspk-research/generative_agents (Apache-2.0), specifically
reverie/backend_server/persona/cognitive_modules/retrieve.py. Ported, not copied:
the scoring math (min-max normalize each component, then weighted sum) matches the
original new_retrieve(); weights and the recency decay are the paper's defaults.

Bring your own embedder (OpenAI/Anthropic/sentence-transformers). Here embeddings
are injected so this file has ZERO third-party deps and runs anywhere.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
import math

# Paper/repo defaults. In reverie these live per-agent in persona.scratch.
RECENCY_DECAY = 0.995          # multiplied per step of access-recency rank
RECENCY_W = 0.5                # gw[0]
IMPORTANCE_W = 3.0             # gw[2] (repo applies importance*3)
RELEVANCE_W = 2.0             # gw[1] (repo applies relevance*2)


@dataclass
class MemoryNode:
    description: str
    embedding: list[float]
    importance: float                       # "poignancy" 1-10 from the LLM
    created: datetime
    last_accessed: datetime
    kind: str = "observation"               # observation | reflection | plan
    evidence: list[int] = field(default_factory=list)  # node ids this derives from


def cos_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _minmax(d: dict[int, float]) -> dict[int, float]:
    if not d:
        return {}
    lo, hi = min(d.values()), max(d.values())
    if hi == lo:                              # avoid divide-by-zero; flat -> mid
        return {k: 0.5 for k in d}
    return {k: (v - lo) / (hi - lo) for k, v in d.items()}


class MemoryStream:
    """Recency + importance + relevance retrieval, faithful to the paper."""

    def __init__(self) -> None:
        self.nodes: list[MemoryNode] = []

    def add(self, node: MemoryNode) -> int:
        self.nodes.append(node)
        return len(self.nodes) - 1

    def retrieve(self, query_embedding: list[float], now: datetime,
                 top_k: int = 5) -> list[tuple[int, MemoryNode, float]]:
        if not self.nodes:
            return []
        # RECENCY: rank by last_accessed (most recent = rank 0), decay^rank.
        order = sorted(range(len(self.nodes)),
                       key=lambda i: self.nodes[i].last_accessed, reverse=True)
        recency = {i: RECENCY_DECAY ** rank for rank, i in enumerate(order)}
        importance = {i: n.importance for i, n in enumerate(self.nodes)}
        relevance = {i: cos_sim(query_embedding, n.embedding)
                     for i, n in enumerate(self.nodes)}

        recency, importance, relevance = (
            _minmax(recency), _minmax(importance), _minmax(relevance))

        scores = {
            i: RECENCY_W * recency[i]
               + IMPORTANCE_W * importance[i]
               + RELEVANCE_W * relevance[i]
            for i in range(len(self.nodes))
        }
        ranked = sorted(scores, key=lambda i: scores[i], reverse=True)[:top_k]
        for i in ranked:                     # retrieval refreshes recency
            self.nodes[i].last_accessed = now
        return [(i, self.nodes[i], scores[i]) for i in ranked]

    def reflection_pressure(self, window: int = 100) -> float:
        """Sum of importance over the most recent events; trigger reflection
        when this crosses your threshold (paper uses ~150)."""
        return sum(n.importance for n in self.nodes[-window:])


if __name__ == "__main__":
    now = datetime(2026, 7, 9, 9, 0, 0)
    ms = MemoryStream()
    ms.add(MemoryNode("Isabella is planning a Valentine's party", [1, 0, 0], 8,
                      now, now))
    ms.add(MemoryNode("The coffee machine is out of beans", [0, 1, 0], 2,
                      now, now))
    ms.add(MemoryNode("Klaus wants to invite Maria to the party", [0.9, 0.1, 0],
                      7, now, now))
    for i, n, s in ms.retrieve([1, 0, 0], now, top_k=2):
        print(f"{s:5.2f}  {n.description}")
    print("reflection_pressure:", ms.reflection_pressure())
