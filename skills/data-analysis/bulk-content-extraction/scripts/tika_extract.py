#!/usr/bin/env python3
"""Bulk-extract text + metadata from a directory tree via a running Apache Tika server.

Zero third-party deps: uses only the stdlib (urllib) as an HTTP client against
Tika's /rmeta/text endpoint. Start the server first (see SKILL.md):
    java -jar tika-server-standard-<ver>.jar --port 9998

Usage:
    python3 tika_extract.py <root_dir> [--server http://localhost:9998]
        [--out corpus.jsonl] [--limit-bytes 200000000] [--write-limit 0]
        [--ext .pdf,.docx] [--skip-existing]

Emits one JSON object per file to --out (default: stdout), each with:
    path, mime, chars, meta (selected keys), text, error (on failure).
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# Metadata keys worth keeping in the corpus; Tika emits dozens of noisy ones.
KEEP_META = (
    "Content-Type", "resourceName", "Content-Length",
    "dc:title", "dc:creator", "title", "Author", "creator",
    "Creation-Date", "dcterms:created", "Last-Modified", "dcterms:modified",
    "xmpTPg:NPages", "meta:page-count", "language", "pdf:PDFVersion",
)
DEFAULT_MAX_BYTES = 200 * 1024 * 1024  # skip files bigger than this


def rmeta(server, path, write_limit):
    """PUT a file to Tika /rmeta/text; return the first (container) metadata dict."""
    url = server.rstrip("/") + "/rmeta/text"
    with open(path, "rb") as fh:
        data = fh.read()
    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Accept", "application/json")
    if write_limit and write_limit > 0:
        req.add_header("writeLimit", str(write_limit))
    with urllib.request.urlopen(req, timeout=300) as resp:
        payload = json.loads(resp.read().decode("utf-8", "replace"))
    # /rmeta returns a JSON array: [container, embedded1, ...]; take the container.
    return payload[0] if isinstance(payload, list) and payload else {}


def iter_files(root, exts):
    for dirpath, _dirs, names in os.walk(root):
        for name in names:
            if name.startswith("."):
                continue
            fp = os.path.join(dirpath, name)
            if exts:
                if os.path.splitext(name)[1].lower() not in exts:
                    continue
            yield fp


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("--server", default=os.environ.get("TIKA_SERVER_ENDPOINT", "http://localhost:9998"))
    ap.add_argument("--out", default="-")
    ap.add_argument("--limit-bytes", type=int, default=DEFAULT_MAX_BYTES)
    ap.add_argument("--write-limit", type=int, default=0, help="max chars of text per file (0 = unlimited)")
    ap.add_argument("--ext", default="", help="comma list e.g. .pdf,.docx (default: all)")
    ap.add_argument("--skip-existing", action="store_true", help="skip paths already in --out")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.root):
        ap.error(f"not a directory: {args.root}")
    exts = {e.strip().lower() for e in args.ext.split(",") if e.strip()}

    done = set()
    if args.skip_existing and args.out != "-" and os.path.exists(args.out):
        with open(args.out, encoding="utf-8") as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["path"])
                except Exception:
                    pass

    out = sys.stdout if args.out == "-" else open(args.out, "a", encoding="utf-8")
    ok = fail = skipped = 0
    try:
        for fp in iter_files(args.root, exts):
            if fp in done:
                skipped += 1
                continue
            rec = {"path": fp}
            try:
                if os.path.getsize(fp) > args.limit_bytes:
                    raise ValueError(f"exceeds --limit-bytes ({args.limit_bytes})")
                meta = rmeta(args.server, fp, args.write_limit)
                text = (meta.get("X-TIKA:content") or "").strip()
                rec["mime"] = meta.get("Content-Type", "")
                rec["chars"] = len(text)
                rec["meta"] = {k: meta[k] for k in KEEP_META if k in meta}
                rec["text"] = text
                ok += 1
            except urllib.error.URLError as e:
                rec["error"] = f"tika/network: {e}"
                fail += 1
            except Exception as e:  # noqa: BLE001 - one bad file must not kill the run
                rec["error"] = f"{type(e).__name__}: {e}"
                fail += 1
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
    finally:
        if out is not sys.stdout:
            out.close()
    print(f"[tika_extract] ok={ok} fail={fail} skipped={skipped}", file=sys.stderr)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
