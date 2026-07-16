#!/usr/bin/env python3
"""Runway Gen-4 Aleph video-to-video: submit + poll one job.

Restyle / relight / recompose an existing clip with a text prompt (and
optional reference image). Uses the official Runway REST API directly so
there is no SDK version drift.

Docs: https://docs.dev.runwayml.com/  (API version 2024-11-06)
Auth: export RUNWAYML_API_SECRET=key_...

Usage:
  python3 runway_v2v.py \
    --video https://cdn.example.com/plate.mp4 \
    --prompt "relight as golden-hour sunset, warm rim light" \
    --ratio 1280:720 --out restyled.mp4

The --video must be a public HTTPS URL or a data: URI (Runway fetches it).
Only stdlib is used, so it runs on the stock macOS python3 (3.9).
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://api.dev.runwayml.com"
API_VERSION = "2024-11-06"          # X-Runway-Version — pin this
MODEL = "gen4_aleph"                # Aleph = Runway's v2v model
POLL_SECONDS = 5                    # API asks for >= 5s between polls
POLL_TIMEOUT = 15 * 60             # give up after 15 minutes
VALID_RATIOS = {
    "1280:720", "720:1280", "1104:832", "960:960", "832:1104",
    "1584:672", "848:480", "640:480",
}


def _to_data_uri(path):
    """Local file -> data: URI so Runway can ingest it without hosting."""
    mime = mimetypes.guess_type(path)[0] or "video/mp4"
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    return "data:%s;base64,%s" % (mime, b64)


def _request(method, path, key, body=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("X-Runway-Version", API_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit("Runway API %s error: %s" % (exc.code, detail))


def submit(key, video_uri, prompt, ratio, seed, reference):
    payload = {
        "model": MODEL,
        "videoUri": video_uri,
        "promptText": prompt,
        "ratio": ratio,
    }
    if seed is not None:
        payload["seed"] = seed
    if reference:
        # references guide style/appearance; one image object is enough
        payload["references"] = [{"type": "image", "uri": reference}]
    resp = _request("POST", "/v1/video_to_video", key, payload)
    task_id = resp.get("id")
    if not task_id:
        raise SystemExit("No task id in response: " + json.dumps(resp))
    return task_id


def poll(key, task_id):
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        task = _request("GET", "/v1/tasks/" + task_id, key)
        status = task.get("status")
        if status == "SUCCEEDED":
            outputs = task.get("output") or []
            if not outputs:
                raise SystemExit("SUCCEEDED but no output url")
            return outputs[0]
        if status in ("FAILED", "CANCELLED"):
            raise SystemExit("Task %s: %s" % (status, task.get("failure", "")))
        # PENDING / RUNNING / THROTTLED
        print("  status=%s progress=%s" % (status, task.get("progress")),
              file=sys.stderr)
        time.sleep(POLL_SECONDS)
    raise SystemExit("Timed out after %ds" % POLL_TIMEOUT)


def download(url, out_path):
    with urllib.request.urlopen(url, timeout=120) as resp, \
            open(out_path, "wb") as fh:
        fh.write(resp.read())


def main():
    ap = argparse.ArgumentParser(description="Runway Gen-4 Aleph v2v")
    ap.add_argument("--video", required=True,
                    help="Input clip: HTTPS URL, data: URI, or local file")
    ap.add_argument("--prompt", required=True, help="Edit instruction (<1000 chars)")
    ap.add_argument("--ratio", default="1280:720", choices=sorted(VALID_RATIOS))
    ap.add_argument("--reference", help="Optional style reference image URL")
    ap.add_argument("--seed", type=int, help="Seed for reproducibility")
    ap.add_argument("--out", default="v2v_out.mp4")
    args = ap.parse_args()

    key = os.environ.get("RUNWAYML_API_SECRET")
    if not key:
        raise SystemExit("Set RUNWAYML_API_SECRET")

    video_uri = args.video
    if not video_uri.startswith(("http://", "https://", "data:")):
        if not os.path.isfile(video_uri):
            raise SystemExit("Not a URL and not a file: " + video_uri)
        video_uri = _to_data_uri(video_uri)

    print("Submitting…", file=sys.stderr)
    task_id = submit(key, video_uri, args.prompt, args.ratio, args.seed,
                     args.reference)
    print("task id: " + task_id, file=sys.stderr)
    url = poll(key, task_id)
    print("Downloading -> " + args.out, file=sys.stderr)
    download(url, args.out)
    print(args.out)


if __name__ == "__main__":
    main()
