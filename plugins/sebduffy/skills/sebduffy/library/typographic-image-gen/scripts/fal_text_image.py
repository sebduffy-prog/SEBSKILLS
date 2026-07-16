#!/usr/bin/env python3
"""Generate a typographic image via any fal.ai text-strong model (stdlib only, py3.9 OK).

Works with the text-legible model family that all share fal's queue + params:
  - fal-ai/flux-2-pro                          (FLUX.2 [pro])
  - fal-ai/bytedance/seedream/v4/text-to-image (Seedream)
  - openai/gpt-image-2                         (GPT Image 2)

Auth: export FAL_KEY=...   (get one at fal.ai/dashboard/keys)

Usage:
  python3 fal_text_image.py --endpoint fal-ai/flux-2-pro \
      --prompt "OOH poster ..." --size landscape_16_9 --seed 7 --out comp.png

--size accepts a fal preset (square_hd, portrait_16_9, landscape_16_9, auto_4K, ...)
or WxH (e.g. 2048x2732). No image is ever fabricated: on API error the script exits non-zero.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error

QUEUE = "https://queue.fal.run/"
POLL_SECONDS = 3
MAX_WAIT_SECONDS = 300


def _req(url, method="GET", body=None):
    key = os.environ.get("FAL_KEY")
    if not key:
        sys.exit("ERROR: set FAL_KEY (export FAL_KEY=...) — never hardcode it.")
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Key " + key)
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit("ERROR: fal HTTP {} — {}".format(e.code, e.read().decode()[:400]))
    except urllib.error.URLError as e:
        sys.exit("ERROR: network — {}".format(e.reason))


def _size(v):
    if v and "x" in v.lower():
        w, h = v.lower().split("x", 1)
        return {"width": int(w), "height": int(h)}
    return v  # preset string, or None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--endpoint", required=True, help="fal model id, e.g. fal-ai/flux-2-pro")
    p.add_argument("--prompt", required=True)
    p.add_argument("--size", default="landscape_4_3", help="fal preset or WxH")
    p.add_argument("--seed", type=int)
    p.add_argument("--out", default="typographic.png")
    a = p.parse_args()

    payload = {"prompt": a.prompt, "num_images": 1}
    sz = _size(a.size)
    if sz is not None:
        payload["image_size"] = sz
    if a.seed is not None:
        payload["seed"] = a.seed

    sub = _req(QUEUE + a.endpoint, "POST", payload)
    status_url = sub.get("status_url")
    response_url = sub.get("response_url")
    if not status_url:
        sys.exit("ERROR: no status_url in submit response: " + json.dumps(sub)[:300])

    waited = 0
    while True:
        st = _req(status_url)
        state = st.get("status")
        if state == "COMPLETED":
            break
        if state in ("FAILED", "ERROR"):
            sys.exit("ERROR: generation failed — " + json.dumps(st)[:400])
        if waited >= MAX_WAIT_SECONDS:
            sys.exit("ERROR: timed out after {}s (last status {})".format(waited, state))
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
        print("  ...{}  ({}s)".format(state, waited), file=sys.stderr)

    result = _req(response_url)
    imgs = result.get("images") or []
    if not imgs or not imgs[0].get("url"):
        sys.exit("ERROR: no image url in result — " + json.dumps(result)[:400])
    urllib.request.urlretrieve(imgs[0]["url"], a.out)
    print("wrote {}  (seed={})".format(a.out, result.get("seed", a.seed)))


if __name__ == "__main__":
    main()
