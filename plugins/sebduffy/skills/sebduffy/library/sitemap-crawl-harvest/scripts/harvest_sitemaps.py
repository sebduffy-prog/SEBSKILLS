#!/usr/bin/env python3
"""Harvest a site's full URL surface from robots.txt + sitemaps (stdlib only).

Walks robots.txt Sitemap: hints, recurses through sitemap-index files and
50k-URL chunks, handles .gz, is namespace-agnostic, cycle-safe, and can filter
by regex. No third-party deps -> runs on the system python3 (3.9+).

Usage:
  python3 harvest_sitemaps.py https://www.example.com
  python3 harvest_sitemaps.py https://ex.com/sitemap.xml --match '/blog/'
  python3 harvest_sitemaps.py https://ex.com --exclude '\\.(jpg|png)$' --jsonl out.jsonl
"""
import argparse
import gzip
import io
import re
import sys
import urllib.request
import urllib.error
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

UA = "Mozilla/5.0 (compatible; sitemap-harvest/1.0; +https://sitemaps.org)"
TIMEOUT = 30
MAX_SITEMAPS = 5000  # safety ceiling on index recursion


def fetch(url):
    """Return decoded bytes for url; transparently gunzip .gz or gzipped bodies."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
    if url.lower().endswith(".gz") or enc == "gzip" or raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except OSError:
            pass  # not actually gzipped
    return raw


def localname(tag):
    """Strip XML namespace: '{ns}loc' -> 'loc'."""
    return tag.rsplit("}", 1)[-1].lower()


def sitemaps_from_robots(base):
    """Yield absolute sitemap URLs declared in robots.txt (may be empty)."""
    robots = urljoin(base, "/robots.txt")
    try:
        text = fetch(robots).decode("utf-8", "replace")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
        return
    for line in text.splitlines():
        if line.strip().lower().startswith("sitemap:"):
            yield line.split(":", 1)[1].strip()


def parse_sitemap(url):
    """Parse one sitemap doc. Returns (child_sitemap_urls, page_records).

    page_records are dicts: {url, lastmod?, priority?, changefreq?}.
    Falls back to line-by-line for plain-text sitemaps.
    """
    body = fetch(url)
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        # plain-text sitemap: one URL per line
        pages = [{"url": ln.strip()} for ln in body.decode("utf-8", "replace").splitlines()
                 if ln.strip().startswith("http")]
        return [], pages

    children, pages = [], []
    for node in root:
        tag = localname(node.tag)
        if tag == "sitemap":  # <sitemapindex> entry -> recurse
            loc = node.find("{*}loc")
            if loc is not None and loc.text:
                children.append(loc.text.strip())
        elif tag == "url":  # <urlset> entry -> a page
            rec = {}
            for child in node:
                ct = localname(child.tag)
                if ct == "loc" and child.text:
                    rec["url"] = child.text.strip()
                elif ct in ("lastmod", "priority", "changefreq") and child.text:
                    rec[ct] = child.text.strip()
            if rec.get("url"):
                pages.append(rec)
    return children, pages


def harvest(start, match=None, exclude=None, same_host=False):
    """BFS over sitemaps from a site root or a sitemap URL. Yields deduped page records."""
    parsed = urlparse(start)
    host = parsed.netloc
    # Seed queue: explicit sitemap URL, else robots.txt hints + conventional path.
    if start.rstrip("/").endswith((".xml", ".xml.gz", ".txt")):
        queue = [start]
    else:
        queue = list(sitemaps_from_robots(start)) or [urljoin(start, "/sitemap.xml")]

    seen_sitemaps, seen_urls = set(), set()
    m_re = re.compile(match) if match else None
    x_re = re.compile(exclude) if exclude else None

    while queue and len(seen_sitemaps) < MAX_SITEMAPS:
        sm = queue.pop(0)
        if sm in seen_sitemaps:
            continue
        seen_sitemaps.add(sm)
        try:
            children, pages = parse_sitemap(sm)
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"# WARN skip {sm}: {e}", file=sys.stderr)
            continue
        for c in children:
            if c not in seen_sitemaps:
                queue.append(c)
        for rec in pages:
            u = rec["url"]
            if u in seen_urls:
                continue
            if same_host and urlparse(u).netloc != host:
                continue
            if m_re and not m_re.search(u):
                continue
            if x_re and x_re.search(u):
                continue
            seen_urls.add(u)
            yield rec


def main():
    ap = argparse.ArgumentParser(description="Harvest URLs from a site's sitemaps.")
    ap.add_argument("start", help="Site root (https://ex.com) or a sitemap URL")
    ap.add_argument("--match", help="Keep only URLs matching this regex")
    ap.add_argument("--exclude", help="Drop URLs matching this regex")
    ap.add_argument("--same-host", action="store_true", help="Keep only URLs on the start host")
    ap.add_argument("--jsonl", help="Also write full records (url+lastmod+priority) to this JSONL file")
    args = ap.parse_args()

    import json
    n = 0
    fh = open(args.jsonl, "w") if args.jsonl else None
    try:
        for rec in harvest(args.start, args.match, args.exclude, args.same_host):
            print(rec["url"])
            if fh:
                fh.write(json.dumps(rec) + "\n")
            n += 1
    finally:
        if fh:
            fh.close()
    print(f"# {n} URLs harvested", file=sys.stderr)


if __name__ == "__main__":
    main()
