#!/usr/bin/env python3
"""Federated knowledge memory: append-only, provenance-tracked claim store.

Stdlib-only (sqlite3 + hashlib + re) so it runs on macOS python3.9 with no pip.
Swap the PII regex for Microsoft Presidio and the near-dup hash for real
embeddings in production -- the seams are marked PROD.

Data model (three immutable, append-only tables):
  claims        one row per distinct fact (keyed by content hash); never mutated
  attestations  one row per independent assertion of a claim (who/model/provider)
  events        promotion / retraction audit trail (bi-temporal, W3C-PROV shaped)

Trust is DERIVED, never stored on the claim: a claim is `trusted` when it has a
promotion event, which the promote() gate only emits on a passing rule.
"""
import argparse, hashlib, json, re, sqlite3, sys, time
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS claims(
  cid TEXT PRIMARY KEY,          -- sha256 of normalized subject|predicate|object
  subject TEXT, predicate TEXT, object TEXT,
  norm TEXT, loosekey TEXT,      -- loosekey = punctuation-insensitive near-dup key (PROD: embedding)
  valid_from TEXT, valid_to TEXT,-- bi-temporal: real-world validity window
  ingested_at TEXT,              -- transaction time (immutable)
  source_uri TEXT, skill TEXT);
CREATE TABLE IF NOT EXISTS attestations(
  cid TEXT, agent TEXT, model TEXT, provider TEXT, evidence TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS events(
  cid TEXT, kind TEXT, reason TEXT, actor TEXT, at TEXT);
CREATE INDEX IF NOT EXISTS ix_att_cid ON attestations(cid);
CREATE INDEX IF NOT EXISTS ix_evt_cid ON events(cid);
"""

# PROD: replace with presidio_analyzer AnalyzerEngine (PERSON, EMAIL, CREDIT_CARD, ...)
PII = [re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),          # email
       re.compile(r"\b(?:\d[ -]?){13,16}\b"),            # card-ish
       re.compile(r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b")]     # ssn-ish

def now(): return datetime.now(timezone.utc).isoformat()
def norm(s): return re.sub(r"\s+", " ", s.strip().lower())
def loose(s): return re.sub(r"[^a-z0-9]+", "", s.lower())  # PROD: replace w/ embedding
def cid_of(s, p, o): return hashlib.sha256(f"{norm(s)}|{norm(p)}|{norm(o)}".encode()).hexdigest()[:16]

def connect(db):
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row; c.executescript(SCHEMA); return c

def scan_pii(*fields):
    return [pat.pattern for f in fields for pat in PII if pat.search(f or "")]

def write(c, subject, predicate, obj, *, agent, model, provider,
          evidence="", source_uri="", skill="", valid_from="", valid_to=""):
    """Ingest a CANDIDATE claim + one attestation. Idempotent by content hash.

    Returns (cid, status) where status in {new, deduped, blocked-pii, near-dup}.
    """
    hits = scan_pii(subject, predicate, obj)
    if hits:
        return None, f"blocked-pii:{','.join(hits)}"
    cid = cid_of(subject, predicate, obj)
    n = norm(f"{subject} {predicate} {obj}")
    row = c.execute("SELECT cid FROM claims WHERE cid=?", (cid,)).fetchone()
    status = "deduped" if row else "new"
    if not row:
        # PROD: cosine(embedding, existing) > 0.92 -> attach to existing cid instead
        dup = c.execute("SELECT cid FROM claims WHERE loosekey=?", (loose(f"{subject}{predicate}{obj}"),)).fetchone()
        if dup:
            cid, status = dup["cid"], "near-dup"
        else:
            c.execute("INSERT INTO claims VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (cid, subject, predicate, obj, n, loose(f"{subject}{predicate}{obj}"),
                       valid_from, valid_to, now(), source_uri, skill))
    c.execute("INSERT INTO attestations VALUES(?,?,?,?,?,?)",
              (cid, agent, model, provider, evidence, now()))
    c.commit()
    return cid, status

def providers(c, cid):
    return {r["provider"] for r in c.execute(
        "SELECT DISTINCT provider FROM attestations WHERE cid=? AND provider!=''", (cid,))}

def is_trusted(c, cid):
    return c.execute("SELECT 1 FROM events WHERE cid=? AND kind='promote'"
                     " AND cid NOT IN (SELECT cid FROM events WHERE kind='retract')",
                     (cid,)).fetchone() is not None

def promote(c, cid, *, quorum=2, steward=None, executed=False, actor="promote-job"):
    """Gate candidate -> trusted. Passes on ANY: cross-provider quorum, steward
    sign-off, execution-verified, or an attestation carrying evidence."""
    if is_trusted(c, cid):
        return "already-trusted"
    has_ev = c.execute("SELECT 1 FROM attestations WHERE cid=? AND evidence!=''",
                       (cid,)).fetchone() is not None
    npro = len(providers(c, cid))
    reason = None
    if npro >= quorum: reason = f"cross-provider-quorum:{npro}"
    elif steward:      reason = f"steward:{steward}"
    elif executed:     reason = "execution-verified"
    elif has_ev:       reason = "evidence-linked"
    if not reason:
        return f"held:providers={npro}<{quorum},no-steward/exec/evidence"
    c.execute("INSERT INTO events VALUES(?,?,?,?,?)", (cid, "promote", reason, actor, now()))
    c.commit()
    return f"promoted:{reason}"

def retract(c, cid, reason, actor):
    c.execute("INSERT INTO events VALUES(?,?,?,?,?)", (cid, "retract", reason, actor, now()))
    c.commit()

def query(c, *, predicate=None, subject=None, trusted_only=True, limit=20):
    """Read ranked shared context. Rank = #distinct providers, then recency.
    Conflicts (same subject+predicate, different object) are KEPT -- both returned,
    higher-authority/more-recent first, so the caller sees the disagreement."""
    rows = c.execute("SELECT * FROM claims WHERE (?='' OR predicate=?) AND (?='' OR subject=?)",
                     (predicate or "", predicate or "", subject or "", subject or "")).fetchall()
    out = []
    for r in rows:
        if trusted_only and not is_trusted(c, r["cid"]):
            continue
        out.append({"cid": r["cid"], "subject": r["subject"], "predicate": r["predicate"],
                    "object": r["object"], "providers": sorted(providers(c, r["cid"])),
                    "trusted": is_trusted(c, r["cid"]), "ingested_at": r["ingested_at"],
                    "source": r["source_uri"], "skill": r["skill"]})
    out.sort(key=lambda x: (len(x["providers"]), x["ingested_at"]), reverse=True)
    return out[:limit]

def _cli():
    ap = argparse.ArgumentParser(description="federated knowledge memory")
    ap.add_argument("--db", default="knowledge.db")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write"); [w.add_argument(a, required=True) for a in
        ("--subject", "--predicate", "--object", "--agent", "--model", "--provider")]
    for a in ("--evidence", "--source-uri", "--skill", "--valid-from", "--valid-to"):
        w.add_argument(a, default="")
    p = sub.add_parser("promote"); p.add_argument("--cid", required=True)
    p.add_argument("--quorum", type=int, default=2); p.add_argument("--steward", default=None)
    p.add_argument("--executed", action="store_true")
    q = sub.add_parser("query"); q.add_argument("--predicate", default=None)
    q.add_argument("--subject", default=None); q.add_argument("--all", action="store_true")
    a = ap.parse_args(); c = connect(a.db)
    if a.cmd == "write":
        cid, st = write(c, a.subject, a.predicate, a.object, agent=a.agent, model=a.model,
                        provider=a.provider, evidence=a.evidence, source_uri=a.source_uri,
                        skill=a.skill, valid_from=a.valid_from, valid_to=a.valid_to)
        print(json.dumps({"cid": cid, "status": st}))
    elif a.cmd == "promote":
        print(promote(c, a.cid, quorum=a.quorum, steward=a.steward, executed=a.executed))
    elif a.cmd == "query":
        print(json.dumps(query(c, predicate=a.predicate, subject=a.subject,
                               trusted_only=not a.all), indent=2))

if __name__ == "__main__":
    _cli()
