#!/usr/bin/env python3
"""Resumable content-addressable scan over a growing file collection.

Walks paths/globs, computes a fast content hash per file, diffs against a
SQLite manifest, and prints which files are NEW / CHANGED / UNCHANGED /
DELETED. The manifest is updated transactionally in batches so an interrupted
run resumes cleanly — re-running only re-hashes files whose size+mtime moved
(cheap stat gate), and only emits NEW/CHANGED for downstream (embed, extract,
index). Stdlib-only fallback (blake2b); uses blake3/xxhash if importable.

Usage:
  scan_manifest.py DB PATH [PATH...] [--glob '**/*.txt'] [--full-hash]
                   [--emit new,changed] [--batch 500] [--json]
Exit: prints newline-delimited "STATUS\tpath" (unless --json summary only).
"""
import argparse, os, sqlite3, sys, glob as globmod, json, time

# ---- pick the fastest available content hasher -----------------------------
def _make_hasher():
    try:
        from blake3 import blake3            # pip install blake3 (Apache-2.0/CC0)
        return "blake3", lambda: blake3()
    except Exception:
        pass
    try:
        import xxhash                         # pip install xxhash
        return "xxh3_128", lambda: xxhash.xxh3_128()
    except Exception:
        pass
    import hashlib                            # always present
    return "blake2b", lambda: hashlib.blake2b(digest_size=16)

HASH_NAME, _new_hasher = _make_hasher()
CHUNK = 1 << 20  # 1 MiB

def content_hash(path):
    h = _new_hasher()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()

# ---- manifest --------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
  path   TEXT PRIMARY KEY,
  size   INTEGER NOT NULL,
  mtime  REAL    NOT NULL,
  chash  TEXT    NOT NULL,     -- content hash (algo in meta)
  seen   INTEGER NOT NULL,     -- run epoch this path was last observed
  ann_key INTEGER              -- optional stable key into the ANN index
);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
"""

def open_db(path):
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")   # crash-safe, concurrent reads
    con.executescript(SCHEMA)
    algo = con.execute("SELECT v FROM meta WHERE k='hash'").fetchone()
    if algo and algo[0] != HASH_NAME:
        sys.exit(f"manifest built with {algo[0]!r} but this run uses "
                 f"{HASH_NAME!r}; hashes are not comparable — rebuild or match algo")
    con.execute("INSERT OR IGNORE INTO meta(k,v) VALUES('hash',?)", (HASH_NAME,))
    con.commit()
    return con

def iter_paths(roots, pattern):
    for root in roots:
        if os.path.isfile(root):
            yield os.path.abspath(root); continue
        for p in globmod.glob(os.path.join(root, pattern), recursive=True):
            if os.path.isfile(p):
                yield os.path.abspath(p)

def scan(con, roots, pattern, full_hash, emit, batch):
    epoch = int(time.time())
    con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('epoch',?)", (str(epoch),))
    cur = con.cursor()
    counts = {"new": 0, "changed": 0, "unchanged": 0, "deleted": 0}
    pending, n = [], 0
    for path in iter_paths(roots, pattern):
        st = os.stat(path)
        row = cur.execute(
            "SELECT size,mtime,chash FROM files WHERE path=?", (path,)).fetchone()
        # stat gate: skip re-hashing when size+mtime unchanged (unless --full-hash)
        if row and not full_hash and row[0] == st.st_size and row[1] == st.st_mtime:
            status, ch = "unchanged", row[2]
        else:
            ch = content_hash(path)
            if row is None:
                status = "new"
            elif ch != row[2]:
                status = "changed"
            else:
                status = "unchanged"
        counts[status] += 1
        pending.append((path, st.st_size, st.st_mtime, ch, epoch))
        if status in emit:
            sys.stdout.write(f"{status.upper()}\t{path}\n")
        n += 1
        if len(pending) >= batch:
            _flush(con, pending); pending = []   # checkpoint: resumable here
    if pending:
        _flush(con, pending)
    # anything not touched this epoch has been deleted from the source
    for (path,) in cur.execute(
            "SELECT path FROM files WHERE seen<?", (epoch,)).fetchall():
        counts["deleted"] += 1
        if "deleted" in emit:
            sys.stdout.write(f"DELETED\t{path}\n")
    con.execute("DELETE FROM files WHERE seen<?", (epoch,))
    con.commit()
    return counts, n

def _flush(con, rows):
    con.executemany(
        "INSERT INTO files(path,size,mtime,chash,seen) VALUES(?,?,?,?,?) "
        "ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime=excluded.mtime, "
        "chash=excluded.chash, seen=excluded.seen", rows)
    con.commit()  # each batch is durable -> Ctrl-C safe, next run continues

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db"); ap.add_argument("paths", nargs="+")
    ap.add_argument("--glob", default="**/*")
    ap.add_argument("--full-hash", action="store_true",
                    help="re-hash every file, ignore the size+mtime fast gate")
    ap.add_argument("--emit", default="new,changed",
                    help="comma list of new,changed,unchanged,deleted to print")
    ap.add_argument("--batch", type=int, default=500)
    ap.add_argument("--json", action="store_true",
                    help="suppress per-file lines, print only the JSON summary")
    a = ap.parse_args()
    emit = set() if a.json else {s.strip() for s in a.emit.split(",") if s.strip()}
    con = open_db(a.db)
    counts, total = scan(con, a.paths, a.glob, a.full_hash, emit, a.batch)
    summary = {"hash": HASH_NAME, "total": total, **counts,
               "manifest": os.path.abspath(a.db)}
    sys.stderr.write(json.dumps(summary) + "\n")
    if a.json:
        print(json.dumps(summary))

if __name__ == "__main__":
    main()
