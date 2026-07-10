#!/usr/bin/env python3
"""Minimal BFL (Black Forest Labs) FLUX client: generate or instruction-edit, poll, download.

No SDK. Only needs `requests` (stdlib fallback below if unavailable).
API key from env BFL_API_KEY (or --key). Header is `x-key`.

Examples:
  # Text-to-image (FLUX.2 pro)
  python flux_bfl.py gen "a cinematic hero shot of a red sports car on a wet street at night" \
      --model flux-2-pro --width 1536 --height 864 -o hero.jpg

  # Instruction edit (FLUX.1 Kontext) — change the input image per an instruction
  python flux_bfl.py edit input.jpg "change the car color to metallic teal, keep everything else" \
      --model flux-kontext-pro --aspect 16:9 -o edited.jpg
"""
import argparse, base64, os, sys, time, json, mimetypes, urllib.request

BASE = os.environ.get("BFL_BASE", "https://api.bfl.ai")  # or api.eu.bfl.ai / api.us.bfl.ai
POLL_TIMEOUT_S = 180
POLL_INTERVAL_S = 1.5

try:
    import requests  # noqa
    def _post(url, headers, body):
        r = requests.post(url, headers=headers, json=body, timeout=60); r.raise_for_status(); return r.json()
    def _get(url, headers):
        r = requests.get(url, headers=headers, timeout=60); r.raise_for_status(); return r.json()
    def _download(url, path):
        r = requests.get(url, timeout=120); r.raise_for_status(); open(path, "wb").write(r.content)
except ImportError:  # stdlib fallback
    def _post(url, headers, body):
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers={**headers, "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as f: return json.load(f)
    def _get(url, headers):
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=60) as f: return json.load(f)
    def _download(url, path):
        with urllib.request.urlopen(url, timeout=120) as f: open(path, "wb").write(f.read())


def submit(model, key, payload):
    url = f"{BASE}/v1/{model}"
    resp = _post(url, {"x-key": key, "Content-Type": "application/json"}, payload)
    pid, poll = resp.get("id"), resp.get("polling_url")
    if not poll:
        sys.exit(f"No polling_url in response: {json.dumps(resp)[:400]}")
    return pid, poll


def poll(poll_url, key):
    deadline = time.time() + POLL_TIMEOUT_S
    while time.time() < deadline:
        r = _get(poll_url, {"x-key": key})
        status = r.get("status")
        if status == "Ready":
            return r["result"]["sample"]  # signed URL, valid ~10 min
        if status in ("Error", "Failed"):
            sys.exit(f"Generation {status}: {json.dumps(r)[:400]}")
        time.sleep(POLL_INTERVAL_S)
    sys.exit("Timed out waiting for result")


def b64_image(path):
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    return "data:%s;base64,%s" % (mime, base64.b64encode(open(path, "rb").read()).decode())


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen"); g.add_argument("prompt")
    g.add_argument("--model", default="flux-2-pro")
    g.add_argument("--width", type=int, default=1024); g.add_argument("--height", type=int, default=1024)
    e = sub.add_parser("edit"); e.add_argument("image"); e.add_argument("prompt")
    e.add_argument("--model", default="flux-kontext-pro"); e.add_argument("--aspect", default=None)
    for p in (g, e):
        p.add_argument("--seed", type=int, default=None)
        p.add_argument("--fmt", default="jpeg", choices=["jpeg", "png"])
        p.add_argument("-o", "--out", default="flux_out.jpg")
        p.add_argument("--key", default=os.environ.get("BFL_API_KEY"))
    a = ap.parse_args()
    if not a.key:
        sys.exit("Set BFL_API_KEY env var or pass --key")

    payload = {"prompt": a.prompt, "output_format": a.fmt}
    if a.seed is not None: payload["seed"] = a.seed
    if a.cmd == "gen":
        payload["width"], payload["height"] = a.width, a.height
    else:
        payload["input_image"] = b64_image(a.image)
        if a.aspect: payload["aspect_ratio"] = a.aspect

    _, poll_url = submit(a.model, a.key, payload)
    signed = poll(poll_url, a.key)
    _download(signed, a.out)
    print(a.out)


if __name__ == "__main__":
    main()
