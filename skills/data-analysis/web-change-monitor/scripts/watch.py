#!/usr/bin/env python3
"""Lightweight web-change monitor: fetch -> extract -> diff vs baseline -> threshold -> notify.

Stdlib-only for text & json modes. css mode needs beautifulsoup4 (pip install).
Baselines are stored one file per watch under --datastore (default ./cd_datastore).

Watchlist JSON (array of objects):
  { "url": "https://...",                 # required
    "mode": "text" | "json" | "css",       # default text
    "selector": ".price" | "data.items.0.name",  # css selector or dotted json path
    "threshold": 0.02,                      # min change ratio (0..1) to count as significant
    "name": "optional label",
    "headers": {"User-Agent": "..."} }      # optional per-watch request headers

Usage:
  python3 watch.py --watchlist watches.json [--datastore DIR] [--webhook URL] [--json]

Exit code 0 = ran OK; the report (stdout, or --json) lists which watches changed.
Schedule with cron/launchd to poll; state persists in the datastore between runs.
"""
import argparse, difflib, hashlib, json, os, re, sys, urllib.request, urllib.error

DEFAULT_UA = "web-change-monitor/1.0 (+stdlib urllib)"
TAG_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.I | re.S)
STRIP_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"[ \t\r\f\v]+")


def fetch(url, headers=None, timeout=30):
    hdrs = {"User-Agent": DEFAULT_UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    ctype = r.headers.get_content_charset() or "utf-8"
    return raw.decode(ctype, errors="replace")


def extract_text(html):
    """Strip scripts/styles/tags, collapse whitespace -> stable text signal."""
    no_sc = TAG_RE.sub(" ", html)
    text = STRIP_RE.sub(" ", no_sc)
    text = WS_RE.sub(" ", text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def extract_json(body, path):
    """Dotted path into JSON, e.g. 'data.items.0.name'. Empty path = whole doc."""
    cur = json.loads(body)
    if not path:
        return json.dumps(cur, sort_keys=True, indent=2)
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return json.dumps(cur, sort_keys=True, indent=2) if isinstance(cur, (dict, list)) else str(cur)


def extract_css(html, selector):
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise SystemExit("css mode needs beautifulsoup4: pip install beautifulsoup4")
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.select(selector) if selector else [soup]
    parts = [n.get_text(" ", strip=True) for n in nodes]
    return WS_RE.sub(" ", "\n".join(p for p in parts if p))


def extract(body, mode, selector):
    if mode == "json":
        return extract_json(body, selector or "")
    if mode == "css":
        return extract_css(body, selector or "")
    return extract_text(body)


def baseline_path(datastore, watch):
    key = watch.get("name") or watch["url"]
    h = hashlib.sha256(key.encode()).hexdigest()[:16]
    return os.path.join(datastore, f"{h}.snapshot")


def change_ratio(old, new):
    """1 - similarity; 0 means identical, 1 means completely different."""
    if old == new:
        return 0.0
    return 1.0 - difflib.SequenceMatcher(None, old, new).ratio()


def diff_preview(old, new, n=12):
    d = difflib.unified_diff(old.splitlines(), new.splitlines(),
                             lineterm="", n=1, fromfile="baseline", tofile="current")
    lines = list(d)
    return "\n".join(lines[:n]) + ("\n..." if len(lines) > n else "")


def notify(webhook, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(webhook, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status
    except urllib.error.URLError as e:
        return f"notify-failed: {e}"


def run_watch(watch, datastore, webhook):
    name = watch.get("name") or watch["url"]
    mode = watch.get("mode", "text")
    threshold = float(watch.get("threshold", 0.0))
    result = {"name": name, "url": watch["url"], "mode": mode,
              "changed": False, "ratio": 0.0, "significant": False}
    try:
        body = fetch(watch["url"], watch.get("headers"))
        current = extract(body, mode, watch.get("selector"))
    except Exception as e:  # noqa: BLE001 - report per-watch, never crash the batch
        result["error"] = f"{type(e).__name__}: {e}"
        return result

    path = baseline_path(datastore, watch)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(current)
        result["first_run"] = True
        return result

    with open(path) as f:
        baseline = f.read()
    ratio = change_ratio(baseline, current)
    result["ratio"] = round(ratio, 4)
    if ratio > 0:
        result["changed"] = True
        result["significant"] = ratio >= threshold
        result["diff"] = diff_preview(baseline, current)
        if result["significant"]:
            with open(path, "w") as f:  # advance baseline only on significant change
                f.write(current)
            if webhook:
                result["notified"] = notify(webhook, {
                    "name": name, "url": watch["url"], "ratio": result["ratio"],
                    "diff": result["diff"]})
    return result


def main():
    ap = argparse.ArgumentParser(description="Watch web pages for meaningful changes.")
    ap.add_argument("--watchlist", required=True)
    ap.add_argument("--datastore", default="cd_datastore")
    ap.add_argument("--webhook", default=os.environ.get("CD_WEBHOOK"))
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    os.makedirs(args.datastore, exist_ok=True)
    with open(args.watchlist) as f:
        watches = json.load(f)
    if not isinstance(watches, list):
        raise SystemExit("watchlist must be a JSON array")

    results = [run_watch(w, args.datastore, args.webhook) for w in watches]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if r.get("error"):
                print(f"[ERR ] {r['name']}: {r['error']}")
            elif r.get("first_run"):
                print(f"[BASE] {r['name']}: baseline saved")
            elif r["significant"]:
                print(f"[CHG!] {r['name']}: ratio={r['ratio']} (>= threshold) "
                      f"{'notified' if r.get('notified') else ''}")
            elif r["changed"]:
                print(f"[chg ] {r['name']}: ratio={r['ratio']} (below threshold, ignored)")
            else:
                print(f"[ ok ] {r['name']}: no change")
    sig = sum(1 for r in results if r.get("significant"))
    if not args.json:
        print(f"--- {sig} significant change(s) of {len(results)} watch(es)")


if __name__ == "__main__":
    main()
