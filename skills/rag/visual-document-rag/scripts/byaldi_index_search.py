#!/usr/bin/env python3
"""Index PDFs/images with a ColPali-family model (via byaldi) and run a visual query.

OCR-free late-interaction retrieval: pages are embedded as images and scored by MaxSim.

Usage:
    python byaldi_index_search.py index  <path> [--model M] [--name N] [--store]
    python byaldi_index_search.py search <name> "<query>" [--model M] [-k 3] [--save DIR]

Requires: Python >=3.10, `pip install byaldi pillow`, poppler (for PDFs), a GPU is advised.
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

DEFAULT_MODEL = "vidore/colqwen2-v1.0"


def _load(model_name: str):
    try:
        from byaldi import RAGMultiModalModel
    except ImportError:
        sys.exit("byaldi not installed. Run: pip install byaldi  (Python >=3.10)")
    return RAGMultiModalModel.from_pretrained(model_name)


def cmd_index(args: argparse.Namespace) -> None:
    src = Path(args.path)
    if not src.exists():
        sys.exit(f"Input not found: {src}")
    rag = _load(args.model)
    rag.index(
        input_path=str(src),
        index_name=args.name,
        store_collection_with_index=args.store,
        overwrite=True,
    )
    print(f"Indexed '{src}' as index '{args.name}' (store_images={args.store}).")


def cmd_search(args: argparse.Namespace) -> None:
    rag = _load(args.model)
    # Re-load an existing on-disk index by name, then query.
    rag = rag.from_index(args.name)
    results = rag.search(args.query, k=args.k)
    save_dir = Path(args.save) if args.save else None
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
    for rank, r in enumerate(results, 1):
        print(f"#{rank}  doc={r['doc_id']}  page={r['page_num']}  score={r['score']:.4f}")
        b64 = r.get("base64")
        if save_dir and b64:
            out = save_dir / f"hit_{rank}_doc{r['doc_id']}_p{r['page_num']}.png"
            out.write_bytes(base64.b64decode(b64))
            print(f"    saved {out}")
        elif save_dir and not b64:
            print("    (no image in index — reindex with --store to save page images)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("index", help="index a PDF, image, or directory")
    pi.add_argument("path")
    pi.add_argument("--model", default=DEFAULT_MODEL)
    pi.add_argument("--name", default="visual_index")
    pi.add_argument("--store", action="store_true", help="keep page images (base64) in index")
    pi.set_defaults(func=cmd_index)

    ps = sub.add_parser("search", help="query an existing index")
    ps.add_argument("name")
    ps.add_argument("query")
    ps.add_argument("--model", default=DEFAULT_MODEL)
    ps.add_argument("-k", type=int, default=3)
    ps.add_argument("--save", help="directory to write retrieved page images into")
    ps.set_defaults(func=cmd_search)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
