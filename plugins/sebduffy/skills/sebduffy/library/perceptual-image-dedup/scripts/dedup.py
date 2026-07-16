#!/usr/bin/env python3
"""Perceptual near-duplicate image clustering.

Walk a directory, compute a 64-bit pHash per image, then cluster images
whose Hamming distance <= threshold using faiss binary range_search
(fast) with a pure-python fallback. Emits JSON clusters to stdout.

Deps: pip install imagehash Pillow  (faiss-cpu optional, big speedup).
Usage: python3 dedup.py <dir> [--hamming 8] [--hash phash] [--json out.json]
"""
import argparse, json, os, sys

IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".heic"}


def walk_images(root):
    for dp, _, files in os.walk(root):
        for f in files:
            if os.path.splitext(f)[1].lower() in IMG_EXT:
                yield os.path.join(dp, f)


def compute_hashes(paths, kind):
    import imagehash
    from PIL import Image
    fn = getattr(imagehash, kind)
    out = []  # (path, packed_uint8_bytes)
    for p in paths:
        try:
            with Image.open(p) as im:
                h = fn(im.convert("RGB"))  # hash_size=8 -> 64 bits
            out.append((p, h.hash.flatten()))
        except Exception as e:  # noqa: BLE001 - skip unreadable, keep going
            print(f"skip {p}: {e}", file=sys.stderr)
    return out


def _union_find(n):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    return find, union


def cluster_faiss(bits, radius):
    import numpy as np
    import faiss
    vecs = np.packbits(np.array(bits, dtype=bool), axis=1)  # (n, 8) uint8
    d = vecs.shape[1] * 8
    index = faiss.IndexBinaryFlat(d)
    index.add(vecs)
    lims, _, ids = index.range_search(vecs, radius)  # radius = max Hamming
    find, union = _union_find(len(bits))
    for i in range(len(bits)):
        for j in ids[lims[i]:lims[i + 1]]:
            if j != i:
                union(i, int(j))
    return find


def cluster_bruteforce(bits, radius):
    import numpy as np
    arr = np.array(bits, dtype=bool)
    find, union = _union_find(len(bits))
    for i in range(len(bits)):
        # Hamming = popcount(xor) across the boolean rows
        dist = np.count_nonzero(arr[i] ^ arr[i + 1:], axis=1)
        for off in np.where(dist <= radius)[0]:
            union(i, i + 1 + int(off))
    return find


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--hamming", type=int, default=8, help="max Hamming distance (0-64)")
    ap.add_argument("--hash", default="phash", choices=["phash", "dhash", "average_hash", "whash"])
    ap.add_argument("--json", help="write clusters to file instead of stdout")
    args = ap.parse_args()

    paths = sorted(walk_images(args.root))
    if not paths:
        sys.exit(f"no images under {args.root}")
    items = compute_hashes(paths, args.hash)
    bits = [b for _, b in items]

    try:
        find = cluster_faiss(bits, args.hamming)
    except ImportError:
        print("faiss not installed -> brute-force O(n^2)", file=sys.stderr)
        find = cluster_bruteforce(bits, args.hamming)

    groups = {}
    for i, (p, _) in enumerate(items):
        groups.setdefault(find(i), []).append(p)
    dups = [sorted(g) for g in groups.values() if len(g) > 1]
    dups.sort(key=lambda g: -len(g))

    out = {"images": len(items), "duplicate_clusters": len(dups),
           "duplicated_files": sum(len(g) for g in dups), "clusters": dups}
    text = json.dumps(out, indent=2)
    if args.json:
        with open(args.json, "w") as fh:
            fh.write(text)
        print(f"{len(dups)} clusters -> {args.json}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
