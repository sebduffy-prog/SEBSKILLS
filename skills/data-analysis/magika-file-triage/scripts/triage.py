#!/usr/bin/env python3
"""Triage a directory of files by TRUE content type.

Uses Google Magika (deep-learning content detector, no libmagic needed) when
available, falling back to the native `file` binary (`/usr/bin/file` on macOS).
Emits one JSONL record per file: path, label, mime, group, score, engine.

Usage:
    python3 triage.py <dir_or_file> [more paths ...] > triage.jsonl

Immutable: never renames/moves/writes user files; only reads + emits JSONL.
"""
import json
import subprocess
import sys
from pathlib import Path

LOW_CONFIDENCE = 0.90  # flag magika predictions below this for review


def iter_files(roots):
    for root in roots:
        p = Path(root)
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not f.is_symlink():
                    yield f


def file_binary_mime(path):
    """Fallback: native `file` command (present on macOS + Linux)."""
    try:
        out = subprocess.run(
            ["file", "--brief", "--mime-type", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        return out.stdout.strip() or "application/octet-stream"
    except Exception:
        return "application/octet-stream"


def record_from_file_binary(path):
    mime = file_binary_mime(path)
    return {
        "path": str(path), "label": mime.split("/")[-1], "mime": mime,
        "group": mime.split("/")[0], "score": None, "engine": "file",
        "low_confidence": False,
    }


def main(argv):
    roots = argv[1:]
    if not roots:
        print("usage: triage.py <path> [path ...]", file=sys.stderr)
        return 2

    files = list(iter_files(roots))
    try:
        from magika import Magika
        m = Magika()
        results = m.identify_paths(files)  # batched, ~ms/file
        for path, res in zip(files, results):
            if not getattr(res, "ok", True):
                rec = record_from_file_binary(path)
            else:
                o = res.output
                rec = {
                    "path": str(path), "label": o.label, "mime": o.mime_type,
                    "group": o.group, "score": round(float(res.score), 4),
                    "engine": "magika",
                    "low_confidence": float(res.score) < LOW_CONFIDENCE,
                }
            print(json.dumps(rec))
    except ImportError:
        print("magika not installed; using `file` fallback", file=sys.stderr)
        for path in files:
            print(json.dumps(record_from_file_binary(path)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
