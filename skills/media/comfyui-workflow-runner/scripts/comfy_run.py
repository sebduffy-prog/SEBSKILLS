#!/usr/bin/env python3
"""Headlessly run a ComfyUI workflow (API format) over HTTP + WebSocket.

Single run:
  comfy_run.py --workflow workflow_api.json --set 6.inputs.text="a koi" --set 3.inputs.seed=42 --out ./out

Batch over CSV (header row = --set paths, one run per data row):
  comfy_run.py --workflow workflow_api.json --csv prompts.csv --out ./out

Requires: pip install requests websocket-client
"""
import argparse
import copy
import csv
import json
import os
import sys
import urllib.parse
import uuid

import requests

try:
    import websocket  # websocket-client
except ImportError:
    websocket = None

WS_TIMEOUT_S = 600  # generous for big SDXL/Flux graphs


def coerce(value):
    """Parse a CLI/CSV string into int/float/bool/JSON where possible, else keep string."""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def apply_override(graph, path, value):
    """Patch graph in place: path like '6.inputs.text'. Returns a NEW graph (immutable)."""
    out = copy.deepcopy(graph)
    keys = path.split(".")
    node = out
    for k in keys[:-1]:
        if k not in node:
            raise KeyError(f"override path '{path}' has no key '{k}' in workflow")
        node = node[k]
    node[keys[-1]] = coerce(value)
    return out


def build_graph(base, overrides):
    """overrides: list of (path, value). Returns new graph with all applied."""
    graph = base
    for path, value in overrides:
        graph = apply_override(graph, path, value)
    return graph


def queue_prompt(server, graph, client_id):
    resp = requests.post(
        f"http://{server}/prompt",
        json={"prompt": graph, "client_id": client_id},
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"[error] /prompt {resp.status_code}: {resp.text[:500]}")
    return resp.json()["prompt_id"]


def wait_ws(server, client_id, prompt_id):
    """Block until the executing:null message for our prompt_id arrives."""
    if websocket is None:
        return wait_poll(server, prompt_id)
    ws = websocket.WebSocket()
    ws.connect(f"ws://{server}/ws?clientId={client_id}", timeout=WS_TIMEOUT_S)
    ws.settimeout(WS_TIMEOUT_S)
    try:
        while True:
            msg = ws.recv()
            if isinstance(msg, bytes):
                continue  # latent preview frame
            data = json.loads(msg)
            if data.get("type") == "executing":
                d = data["data"]
                if d.get("node") is None and d.get("prompt_id") == prompt_id:
                    return
    finally:
        ws.close()


def wait_poll(server, prompt_id, interval=1.0):
    import time
    while True:
        h = requests.get(f"http://{server}/history/{prompt_id}", timeout=30).json()
        if prompt_id in h and h[prompt_id].get("outputs"):
            return
        time.sleep(interval)


def download_outputs(server, prompt_id, out_dir, prefix=None):
    h = requests.get(f"http://{server}/history/{prompt_id}", timeout=30).json()
    outputs = h.get(prompt_id, {}).get("outputs", {})
    os.makedirs(out_dir, exist_ok=True)
    saved = []
    for node_id, node_out in outputs.items():
        for img in node_out.get("images", []):
            params = urllib.parse.urlencode(
                {"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")}
            )
            data = requests.get(f"http://{server}/view?{params}", timeout=60).content
            name = f"{prefix + '_' if prefix else ''}{prompt_id[:8]}_{img['filename']}"
            dest = os.path.join(out_dir, name)
            with open(dest, "wb") as f:
                f.write(data)
            saved.append(dest)
            print(f"saved {dest}")
    if not saved:
        print(f"[warn] no image outputs for {prompt_id} (SaveImage node present?)", file=sys.stderr)
    return saved


def run_one(server, base_graph, overrides, out_dir):
    graph = build_graph(base_graph, overrides)
    prefix = None
    for path, val in overrides:
        if path.endswith("filename_prefix"):
            prefix = str(val)
    client_id = str(uuid.uuid4())
    prompt_id = queue_prompt(server, graph, client_id)
    print(f"queued {prompt_id}")
    wait_ws(server, client_id, prompt_id)
    return download_outputs(server, prompt_id, out_dir, prefix)


def parse_set(items):
    out = []
    for it in items or []:
        if "=" not in it:
            sys.exit(f"[error] --set must be PATH=VALUE, got: {it}")
        path, value = it.split("=", 1)
        out.append((path, value))
    return out


def main():
    ap = argparse.ArgumentParser(description="Run a ComfyUI API-format workflow headlessly.")
    ap.add_argument("--server", default="127.0.0.1:8188")
    ap.add_argument("--workflow", required=True, help="workflow_api.json (Save (API Format))")
    ap.add_argument("--set", dest="sets", action="append", help="NODEID.inputs.FIELD=VALUE (repeatable)")
    ap.add_argument("--csv", help="CSV: header row = --set paths, one run per data row")
    ap.add_argument("--out", default="./out")
    args = ap.parse_args()

    with open(args.workflow) as f:
        base_graph = json.load(f)

    if args.csv:
        with open(args.csv, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print(f"batch: {len(rows)} rows")
        for i, row in enumerate(rows, 1):
            overrides = [(k, v) for k, v in row.items() if k and v != ""]
            print(f"--- row {i}/{len(rows)}: {overrides}")
            run_one(args.server, base_graph, overrides, args.out)
    else:
        run_one(args.server, base_graph, parse_set(args.sets), args.out)


if __name__ == "__main__":
    main()
