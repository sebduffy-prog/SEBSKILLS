#!/usr/bin/env python3
"""Durable human-in-the-loop approval gate — framework-agnostic, stdlib only.

Any agent/script (LangGraph or not) can gate a consequential action behind a
persisted approval. State lives in a SQLite file, so a pending request SURVIVES
a process crash/restart: submit in run A, approve out-of-band, enforce in run B.

CLI:
  gate.py submit  <action> --payload '{"to":"cfo@x.com"}' [--db PATH]
  gate.py list    [--status pending] [--db PATH]
  gate.py approve <id> --by seb [--note "ok"] [--db PATH]
  gate.py reject  <id> --by seb [--note "no"] [--db PATH]
  gate.py enforce <id> [--db PATH]   # exit 0 approved, 10 pending, 20 rejected

Library:
  g = Gate("approvals.db")
  rid = g.submit("send_email", {"to": "cfo@x.com", "subject": "Q3"})
  # ...another process, another day...
  g.approve(rid, by="seb", note="looks right")
  g.enforce(rid)  # raises PendingApproval / Rejected until approved
"""
from __future__ import annotations  # py3.9: defer `dict | None` annotations

import argparse
import json
import sqlite3
import sys
import time
import uuid

PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"


class PendingApproval(Exception):
    """Raised by enforce() when a request is still awaiting a human."""


class Rejected(Exception):
    """Raised by enforce() when a human rejected the request."""


class Gate:
    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS approvals ("
                "id TEXT PRIMARY KEY, action TEXT NOT NULL, payload TEXT, "
                "status TEXT NOT NULL, decided_by TEXT, note TEXT, "
                "created REAL NOT NULL, decided REAL)"
            )

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def submit(self, action: str, payload: dict | None = None) -> str:
        rid = uuid.uuid4().hex[:12]
        with self._conn() as c:
            c.execute(
                "INSERT INTO approvals (id, action, payload, status, created) "
                "VALUES (?,?,?,?,?)",
                (rid, action, json.dumps(payload or {}), PENDING, time.time()),
            )
        return rid

    def get(self, rid: str) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT * FROM approvals WHERE id=?", (rid,)).fetchone()
        if row is None:
            raise KeyError(f"no approval request with id {rid!r}")
        return dict(row)

    def _decide(self, rid: str, status: str, by: str, note: str = "") -> dict:
        cur = self.get(rid)
        if cur["status"] != PENDING:
            raise ValueError(f"{rid} already {cur['status']}, cannot set {status}")
        with self._conn() as c:
            c.execute(
                "UPDATE approvals SET status=?, decided_by=?, note=?, decided=? "
                "WHERE id=?",
                (status, by, note, time.time(), rid),
            )
        return self.get(rid)

    def approve(self, rid: str, by: str, note: str = "") -> dict:
        return self._decide(rid, APPROVED, by, note)

    def reject(self, rid: str, by: str, note: str = "") -> dict:
        return self._decide(rid, REJECTED, by, note)

    def list(self, status: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM approvals", ()
        if status:
            q += " WHERE status=?"
            args = (status,)
        q += " ORDER BY created"
        with self._conn() as c:
            return [dict(r) for r in c.execute(q, args).fetchall()]

    def enforce(self, rid: str) -> dict:
        """Return the record if approved; raise otherwise. Idempotent guard to
        put immediately before the consequential action."""
        rec = self.get(rid)
        if rec["status"] == APPROVED:
            return rec
        if rec["status"] == REJECTED:
            raise Rejected(f"{rid} rejected by {rec['decided_by']}: {rec['note']}")
        raise PendingApproval(f"{rid} awaiting approval for action {rec['action']!r}")


def _main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Durable HITL approval gate")
    p.add_argument("--db", default="approvals.db")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit"); s.add_argument("action"); s.add_argument("--payload", default="{}")
    lp = sub.add_parser("list"); lp.add_argument("--status")
    for name in ("approve", "reject"):
        d = sub.add_parser(name); d.add_argument("id"); d.add_argument("--by", required=True); d.add_argument("--note", default="")
    e = sub.add_parser("enforce"); e.add_argument("id")
    a = p.parse_args(argv)
    g = Gate(a.db)

    if a.cmd == "submit":
        print(g.submit(a.action, json.loads(a.payload)))
    elif a.cmd == "list":
        print(json.dumps(g.list(a.status), indent=2))
    elif a.cmd in ("approve", "reject"):
        print(json.dumps(getattr(g, a.cmd)(a.id, a.by, a.note), indent=2))
    elif a.cmd == "enforce":
        try:
            g.enforce(a.id); print("approved"); return 0
        except PendingApproval as ex:
            print(ex, file=sys.stderr); return 10
        except Rejected as ex:
            print(ex, file=sys.stderr); return 20
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
