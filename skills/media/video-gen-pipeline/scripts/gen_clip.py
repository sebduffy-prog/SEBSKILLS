#!/usr/bin/env python3
"""Generate one AI video clip via the fal.ai queue REST API and download it.

Works for any text-to-video (or image-to-video) endpoint on fal — you pass the
endpoint id and the input JSON; only the endpoint string and input fields change
between models. Submit -> poll status_url -> fetch response_url -> download .mp4.

Usage:
  export FAL_KEY=...
  python gen_clip.py --endpoint fal-ai/veo3.1 --out shot1.mp4 \
      --input '{"prompt":"a red sports car drifting through neon Tokyo, night","aspect_ratio":"16:9","duration":"8s","resolution":"1080p"}'

  # image-to-video (first-frame conditioning): put image_url in the input JSON
  python gen_clip.py --endpoint fal-ai/kling-video/v2.1/pro/image-to-video --out shot2.mp4 \
      --input '{"prompt":"camera pushes in, hair blowing","image_url":"https://.../frame.jpg","duration":"5"}'

Only depends on the Python stdlib (urllib) — no SDK, no pip install.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error

QUEUE = "https://queue.fal.run"


def _req(url, method="GET", body=None):
    key = os.environ.get("FAL_KEY")
    if not key:
        sys.exit("ERROR: set FAL_KEY (export FAL_KEY=...) — get one at fal.ai/dashboard/keys")
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Authorization": f"Key {key}",
                                        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR {e.code} on {url}: {e.read().decode()[:500]}")


def _find_video_url(obj):
    """Walk the result JSON for the first {'url': ...} that looks like a video."""
    if isinstance(obj, dict):
        u = obj.get("url")
        if isinstance(u, str) and (u.endswith(".mp4") or "video" in obj or obj.get("content_type", "").startswith("video")):
            return u
        for v in obj.values():
            r = _find_video_url(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_video_url(v)
            if r:
                return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True, help="fal model id, e.g. fal-ai/veo3.1")
    ap.add_argument("--input", required=True, help="JSON string of the model input body")
    ap.add_argument("--out", required=True, help="output .mp4 path")
    ap.add_argument("--poll", type=int, default=6, help="seconds between status polls")
    ap.add_argument("--timeout", type=int, default=900, help="max seconds to wait")
    a = ap.parse_args()

    try:
        inp = json.loads(a.input)
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: --input is not valid JSON: {e}")

    print(f"submit -> {a.endpoint}", file=sys.stderr)
    sub = _req(f"{QUEUE}/{a.endpoint}", method="POST", body=inp)
    status_url = sub.get("status_url")
    response_url = sub.get("response_url")
    if not status_url:
        sys.exit(f"ERROR: no status_url in submit response: {json.dumps(sub)[:400]}")

    deadline = time.time() + a.timeout
    while True:
        st = _req(status_url)
        s = st.get("status")
        print(f"  status={s}", file=sys.stderr)
        if s == "COMPLETED":
            break
        if s in ("FAILED", "ERROR", "CANCELLED"):
            sys.exit(f"ERROR: generation {s}: {json.dumps(st)[:400]}")
        if time.time() > deadline:
            sys.exit("ERROR: timed out waiting for generation")
        time.sleep(a.poll)

    result = _req(response_url)
    url = _find_video_url(result)
    if not url:
        sys.exit(f"ERROR: no video url in result: {json.dumps(result)[:600]}")

    print(f"download -> {a.out}", file=sys.stderr)
    urllib.request.urlretrieve(url, a.out)
    print(a.out)  # stdout = the path, for scripting


if __name__ == "__main__":
    main()
