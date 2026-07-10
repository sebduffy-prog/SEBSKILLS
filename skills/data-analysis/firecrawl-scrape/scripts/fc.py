#!/usr/bin/env python3
"""Dependency-free Firecrawl v2 client (stdlib urllib only).

Use when you do NOT want to pip-install firecrawl-py. Handles scrape, map,
and crawl (with polling). Reads FIRECRAWL_API_KEY from the environment.

Usage:
  export FIRECRAWL_API_KEY=fc-...
  python3 fc.py scrape https://firecrawl.dev            # -> markdown to stdout
  python3 fc.py scrape https://x.com --json '<jsonschema>'  # structured JSON
  python3 fc.py map https://firecrawl.dev --search pricing  # discover URLs
  python3 fc.py crawl https://docs.firecrawl.dev --limit 50 # poll to completion
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("FIRECRAWL_BASE", "https://api.firecrawl.dev/v2")
POLL_SECONDS = 3
POLL_TIMEOUT = 600  # 10 min cap on crawl polling


def _key() -> str:
    k = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not k:
        sys.exit("ERROR: set FIRECRAWL_API_KEY (get one at https://firecrawl.dev)")
    return k


def _req(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_key()}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"HTTP {e.code} on {method} {path}: {detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error on {method} {path}: {e.reason}")


def cmd_scrape(args) -> None:
    formats: list = ["markdown"]
    if args.json:
        schema = json.loads(args.json)
        fmt = {"type": "json", "schema": schema}
        if args.prompt:
            fmt["prompt"] = args.prompt
        formats = [fmt]
    body = {"url": args.url, "formats": formats, "onlyMainContent": True}
    out = _req("POST", "/scrape", body).get("data", {})
    if args.json:
        print(json.dumps(out.get("json", {}), indent=2, ensure_ascii=False))
    else:
        print(out.get("markdown", ""))


def cmd_map(args) -> None:
    body = {"url": args.url}
    if args.search:
        body["search"] = args.search
    links = _req("POST", "/map", body).get("links", [])
    for link in links:
        print(link.get("url") if isinstance(link, dict) else link)


def cmd_crawl(args) -> None:
    body = {"url": args.url, "limit": args.limit,
            "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True}}
    job = _req("POST", "/crawl", body)
    job_id = job.get("id")
    if not job_id:
        sys.exit(f"No crawl id returned: {job}")
    sys.stderr.write(f"crawl started id={job_id}; polling...\n")
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        status = _req("GET", f"/crawl/{job_id}")
        state = status.get("status")
        sys.stderr.write(
            f"  {state} {status.get('completed', 0)}/{status.get('total', '?')}\n")
        if state == "completed":
            json.dump(status.get("data", []), sys.stdout, indent=2, ensure_ascii=False)
            print()
            return
        if state == "failed":
            sys.exit(f"crawl failed: {status}")
        time.sleep(POLL_SECONDS)
    sys.exit("crawl polling timed out")


def main() -> None:
    p = argparse.ArgumentParser(description="Dependency-free Firecrawl v2 client")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scrape")
    s.add_argument("url")
    s.add_argument("--json", help="JSON Schema string for structured extraction")
    s.add_argument("--prompt", help="Natural-language extraction hint (with --json)")
    s.set_defaults(func=cmd_scrape)

    m = sub.add_parser("map")
    m.add_argument("url")
    m.add_argument("--search", help="Rank URLs by relevance to this term")
    m.set_defaults(func=cmd_map)

    c = sub.add_parser("crawl")
    c.add_argument("url")
    c.add_argument("--limit", type=int, default=50)
    c.set_defaults(func=cmd_crawl)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
