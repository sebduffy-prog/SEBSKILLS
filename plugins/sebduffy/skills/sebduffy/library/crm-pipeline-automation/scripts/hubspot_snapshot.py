#!/usr/bin/env python3
"""HubSpot CRM helper: paginate an object, dedup by a property, snapshot a pipeline.

Pure stdlib (urllib) so it runs on macOS system Python 3.9 with no pip installs.
Auth: private-app token in env HUBSPOT_TOKEN (Authorization: Bearer ...).

Usage:
  export HUBSPOT_TOKEN=pat-xxxx
  # Dump all contacts (email,firstname,lastname) to CSV:
  python3 hubspot_snapshot.py dump contacts --props email,firstname,lastname --out contacts.csv
  # Find duplicate contacts sharing an email:
  python3 hubspot_snapshot.py dedup contacts --key email --out dupes.csv
  # Snapshot open deals grouped by pipeline stage:
  python3 hubspot_snapshot.py pipeline --pipeline default --out snapshot.csv

Read-only by default. Nothing is written back to HubSpot.
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.hubapi.com"
PAGE_SIZE = 100  # HubSpot list cap is 100 per page; search cap is 200.
MAX_RETRIES = 4


def _token():
    tok = os.environ.get("HUBSPOT_TOKEN")
    if not tok:
        sys.exit("ERROR: set HUBSPOT_TOKEN (a private-app access token, starts 'pat-').")
    return tok


def _request(method, path, params=None, body=None):
    """Single authenticated call with 429/5xx backoff. Returns parsed JSON."""
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "Authorization": "Bearer " + _token(),
        "Content-Type": "application/json",
    }
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            # 429 = rate limit, 5xx = transient. Honour Retry-After if present.
            if exc.code == 429 or exc.code >= 500:
                wait = float(exc.headers.get("Retry-After", 2 ** attempt))
                time.sleep(wait)
                continue
            detail = exc.read().decode(errors="replace")
            sys.exit("HTTP %s on %s: %s" % (exc.code, path, detail))
    sys.exit("Gave up after %d retries on %s" % (MAX_RETRIES, path))


def paginate(obj, props):
    """Yield every record of an object via the v3 list endpoint (auto-paged)."""
    after = None
    while True:
        params = {"limit": PAGE_SIZE, "properties": ",".join(props)}
        if after:
            params["after"] = after
        page = _request("GET", "/crm/v3/objects/%s" % obj, params=params)
        for row in page.get("results", []):
            yield row
        paging = page.get("paging", {}).get("next")
        if not paging:
            break
        after = paging["after"]


def cmd_dump(obj, props, out):
    with open(out, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id"] + props)
        n = 0
        for rec in paginate(obj, props):
            p = rec.get("properties", {})
            writer.writerow([rec["id"]] + [p.get(k, "") for k in props])
            n += 1
    print("Wrote %d %s to %s" % (n, obj, out))


def cmd_dedup(obj, key, out):
    """Group records by a normalised key value; emit only groups with >1 member."""
    seen = {}
    for rec in paginate(obj, [key]):
        val = (rec.get("properties", {}).get(key) or "").strip().lower()
        if not val:
            continue
        seen.setdefault(val, []).append(rec["id"])
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    with open(out, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([key, "count", "ids"])
        for val, ids in sorted(dupes.items(), key=lambda kv: -len(kv[1])):
            writer.writerow([val, len(ids), " ".join(ids)])
    print("Found %d duplicate %s values (see %s)" % (len(dupes), key, out))


def cmd_pipeline(pipeline, out):
    """Snapshot deals in a pipeline: count + summed amount per stage."""
    props = ["dealname", "amount", "dealstage", "pipeline"]
    stages = {}
    for rec in paginate("deals", props):
        p = rec.get("properties", {})
        if pipeline and p.get("pipeline") != pipeline:
            continue
        stage = p.get("dealstage", "unknown")
        amount = float(p.get("amount") or 0)
        agg = stages.setdefault(stage, {"count": 0, "amount": 0.0})
        agg["count"] += 1
        agg["amount"] += amount
    with open(out, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["dealstage", "deal_count", "total_amount"])
        for stage, agg in sorted(stages.items(), key=lambda kv: -kv[1]["amount"]):
            writer.writerow([stage, agg["count"], round(agg["amount"], 2)])
    print("Snapshot of pipeline '%s' -> %s (%d stages)" % (pipeline, out, len(stages)))


def _opt(args, flag, default=None):
    return args[args.index(flag) + 1] if flag in args else default


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd = argv[1]
    args = argv[2:]
    if cmd == "dump":
        props = _opt(args, "--props", "email,firstname,lastname").split(",")
        cmd_dump(args[0], props, _opt(args, "--out", "dump.csv"))
    elif cmd == "dedup":
        cmd_dedup(args[0], _opt(args, "--key", "email"), _opt(args, "--out", "dupes.csv"))
    elif cmd == "pipeline":
        cmd_pipeline(_opt(args, "--pipeline", "default"), _opt(args, "--out", "snapshot.csv"))
    else:
        sys.exit("Unknown command %r. See --help in the docstring." % cmd)


if __name__ == "__main__":
    main(sys.argv)
