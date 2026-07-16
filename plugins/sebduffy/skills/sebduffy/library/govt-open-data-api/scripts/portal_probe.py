#!/usr/bin/env python3
"""Probe a government open-data portal and identify its platform (CKAN vs Socrata).

Usage:
    python3 portal_probe.py https://data.gov.uk
    python3 portal_probe.py data.cityofchicago.org

Prints the detected platform and a ready-to-use search endpoint. Pure stdlib.
"""
import json
import sys
import urllib.request
import urllib.error

TIMEOUT = 20


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "portal-probe/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read()


def probe(base):
    base = base.rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base
    # CKAN: Action API status endpoint returns {"success": true, ...}
    try:
        status, body = _get(f"{base}/api/3/action/status_show")
        data = json.loads(body)
        if isinstance(data, dict) and "success" in data:
            return {
                "platform": "ckan",
                "search": f"{base}/api/3/action/package_search?q=QUERY&rows=50",
                "package": f"{base}/api/3/action/package_show?id=DATASET_ID",
            }
    except (urllib.error.URLError, ValueError, TimeoutError):
        pass
    # Socrata: discovery metadata endpoint
    try:
        host = base.split("//", 1)[1]
        status, body = _get(f"https://api.us.socrata.com/api/catalog/v1?domains={host}&limit=1")
        data = json.loads(body)
        if isinstance(data, dict) and "results" in data:
            return {
                "platform": "socrata",
                "catalog": f"https://api.us.socrata.com/api/catalog/v1?domains={host}&q=QUERY",
                "resource": f"{base}/resource/FOUR-BY4.json?$where=...&$limit=1000",
            }
    except (urllib.error.URLError, ValueError, TimeoutError, IndexError):
        pass
    return {"platform": "unknown", "hint": "Check the portal's own /developer or /api docs page."}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    print(json.dumps(probe(sys.argv[1]), indent=2))
