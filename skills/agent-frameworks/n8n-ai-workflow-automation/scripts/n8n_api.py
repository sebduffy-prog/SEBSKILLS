#!/usr/bin/env python3
"""Minimal n8n Public REST API client (stdlib only, Python 3.9+).

Talks to the n8n Public API at {BASE}/api/v1 using an API key created in
n8n Settings -> API. No third-party deps.

Env:
  N8N_BASE_URL   default http://localhost:5678
  N8N_API_KEY    required (Settings -> n8n API -> Create an API key)

Usage:
  python3 n8n_api.py list
  python3 n8n_api.py create workflow.json
  python3 n8n_api.py activate <workflow_id>
  python3 n8n_api.py deactivate <workflow_id>
  python3 n8n_api.py get <workflow_id>
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("N8N_BASE_URL", "http://localhost:5678").rstrip("/")
KEY = os.environ.get("N8N_API_KEY", "")


def _request(method, path, payload=None):
    if not KEY:
        sys.exit("ERROR: set N8N_API_KEY (Settings -> n8n API -> Create an API key).")
    url = f"{BASE}/api/v1{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-N8N-API-KEY", KEY)
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        sys.exit(f"HTTP {exc.code} on {method} {path}: {exc.read().decode()[:500]}")
    except urllib.error.URLError as exc:
        sys.exit(f"Connection failed to {url}: {exc.reason}")


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd = argv[0]
    if cmd == "list":
        out = _request("GET", "/workflows?limit=50")
        for wf in out.get("data", []):
            flag = "on " if wf.get("active") else "off"
            print(f"[{flag}] {wf.get('id')}\t{wf.get('name')}")
    elif cmd == "create":
        with open(argv[1]) as fh:
            wf = json.load(fh)
        # Public API accepts name/nodes/connections/settings on create.
        clean = {k: wf[k] for k in ("name", "nodes", "connections", "settings") if k in wf}
        clean.setdefault("settings", {})
        out = _request("POST", "/workflows", clean)
        print(f"Created workflow id={out.get('id')} name={out.get('name')}")
    elif cmd in ("activate", "deactivate"):
        out = _request("POST", f"/workflows/{argv[1]}/{cmd}")
        print(f"{cmd}d {out.get('id')} -> active={out.get('active')}")
    elif cmd == "get":
        print(json.dumps(_request("GET", f"/workflows/{argv[1]}"), indent=2))
    else:
        sys.exit(f"Unknown command: {cmd}\n{__doc__}")


if __name__ == "__main__":
    main(sys.argv[1:])
