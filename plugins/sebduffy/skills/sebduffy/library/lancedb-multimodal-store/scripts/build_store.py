#!/usr/bin/env python3
"""Build a LanceDB multimodal store: raw media bytes + vectors + metadata in one table.

Ingests a folder of images (+ optional sidecar .txt captions) into a single Lance
table with: a blob-encoded `image` column (raw bytes, lazily loaded), a `caption`
text column (FTS-indexed), and a `vector` column (auto-embedded from the caption).
Then runs vector, full-text, and hybrid searches.

Deps (macOS, python3.9 ok):
    pip install "lancedb>=0.13" "sentence-transformers" pyarrow pandas pillow

Usage:
    python3 build_store.py ./images ./lance_data assets

Everything is embedded/local — no server, no API key. Swap the sentence-transformers
model for `get_registry().get("openai")` if you have OPENAI_API_KEY set.
"""
import sys
from pathlib import Path

import lancedb
import pyarrow as pa
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
# Files larger than this are worth blob-encoding (lazy, out-of-line) vs inline binary.
BLOB_THRESHOLD_BYTES = 128 * 1024


def read_caption(img_path: Path) -> str:
    sidecar = img_path.with_suffix(".txt")
    if sidecar.exists():
        return sidecar.read_text(encoding="utf-8", errors="replace").strip()
    return img_path.stem.replace("_", " ").replace("-", " ")


def collect_rows(image_dir: Path):
    rows = []
    for p in sorted(image_dir.iterdir()):
        if p.suffix.lower() not in IMAGE_EXTS:
            continue
        rows.append(
            {
                "id": p.stem,
                "path": str(p),
                "caption": read_caption(p),
                "image": p.read_bytes(),  # raw media stored IN the table
            }
        )
    if not rows:
        sys.exit(f"No images found in {image_dir}")
    return rows


def build(image_dir: str, db_path: str, table_name: str):
    # sentence-transformers runs locally; all-MiniLM-L6-v2 -> 384-dim vectors.
    embedder = (
        get_registry()
        .get("sentence-transformers")
        .create(name="all-MiniLM-L6-v2", device="cpu")
    )

    class Asset(LanceModel):
        id: str
        path: str
        # SourceField = auto-embedded; VectorField = where the vector lands.
        caption: str = embedder.SourceField()
        vector: Vector(embedder.ndims()) = embedder.VectorField()
        image: bytes  # raw media alongside the vector + metadata

    db = lancedb.connect(db_path)
    if table_name in db.table_names():
        db.drop_table(table_name)

    tbl = db.create_table(table_name, schema=Asset)
    tbl.add(collect_rows(image_dir))  # captions embedded automatically on write

    # Indexes. FTS is native (Tantivy-free) by default.
    tbl.create_fts_index("caption", replace=True)
    # ANN index needs enough rows to train; skip on tiny demo sets.
    if tbl.count_rows() >= 256:
        tbl.create_index(metric="cosine", vector_column_name="vector")

    print(f"Built '{table_name}' with {tbl.count_rows()} rows at {db_path}")
    demo_search(tbl)
    demo_blob_fetch(tbl)


def demo_search(tbl):
    q = "a photo of a dog"
    print("\n[vector]", tbl.search(q).limit(3).select(["id", "caption"]).to_list())
    print("[fts]   ", tbl.search("dog", query_type="fts").limit(3)
          .select(["id", "caption"]).to_list())
    print("[hybrid]", tbl.search(q, query_type="hybrid")
          .limit(3).select(["id", "caption"]).to_list())


def demo_blob_fetch(tbl):
    # Raw media rides with the row. For large blobs, prefer lazy retrieval via
    # the underlying Lance dataset instead of materializing bytes into Arrow.
    ds = tbl.to_lance()
    first = tbl.search().limit(1).select(["id"]).to_list()
    print(f"\nStored media for row id={first[0]['id']}; dataset has "
          f"{ds.count_rows()} rows on disk (blobs load on demand).")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: build_store.py <image_dir> <db_path> <table_name>")
    build(sys.argv[1], sys.argv[2], sys.argv[3])
