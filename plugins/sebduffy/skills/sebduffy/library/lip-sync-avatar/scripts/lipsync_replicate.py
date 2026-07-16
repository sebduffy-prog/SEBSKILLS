#!/usr/bin/env python3
"""Run an open lip-sync model on Replicate: upload local face + audio, download the mp4.

No GPU needed locally — Replicate rents one per call. Requires:
    pip install replicate
    export REPLICATE_API_TOKEN=r8_...

Usage:
    python3 lipsync_replicate.py --face face.mp4 --audio vo.wav --model latentsync --out talking.mp4
    python3 lipsync_replicate.py --face photo.jpg --audio vo.wav --model wav2lip --pads "0 20 0 0"
"""
import argparse
import os
import sys
import urllib.request

# model key -> (replicate slug, input-field names for face + audio)
MODELS = {
    "latentsync": ("bytedance/latentsync", "video", "audio"),
    "wav2lip": ("devxpy/cog-wav2lip", "face", "audio"),
    "sadtalker": ("cjwbw/sadtalker", "source_image", "driven_audio"),
}


def parse_args(argv):
    p = argparse.ArgumentParser(description="Lip-sync a face to audio via Replicate.")
    p.add_argument("--face", required=True, help="face image or video (no spaces in path)")
    p.add_argument("--audio", required=True, help="driving audio (wav/mp3)")
    p.add_argument("--model", default="latentsync", choices=sorted(MODELS),
                   help="open model to run (default: latentsync)")
    p.add_argument("--out", default="talking.mp4", help="output mp4 path")
    p.add_argument("--pads", default=None,
                   help='wav2lip only: face padding "top bottom left right", e.g. "0 20 0 0"')
    return p.parse_args(argv)


def validate(args):
    """Fail fast at the boundary before spending an API call."""
    if not os.environ.get("REPLICATE_API_TOKEN"):
        sys.exit("REPLICATE_API_TOKEN is not set — export your Replicate token first.")
    for path in (args.face, args.audio):
        if not os.path.isfile(path):
            sys.exit(f"input not found: {path}")
        if " " in path:
            sys.exit(f"filename has a space (breaks several models): {path}")


def build_input(args):
    _slug, face_field, audio_field = MODELS[args.model]
    payload = {
        face_field: open(args.face, "rb"),
        audio_field: open(args.audio, "rb"),
    }
    if args.model == "wav2lip" and args.pads:
        payload["pads"] = args.pads
    return payload


def download(url, out_path):
    urllib.request.urlretrieve(url, out_path)
    print(f"saved -> {out_path}")


def main(argv):
    args = parse_args(argv)
    validate(args)
    try:
        import replicate  # deferred so --help works without the dep installed
    except ImportError:
        sys.exit("replicate not installed — run: pip install replicate")

    slug = MODELS[args.model][0]
    print(f"running {slug} ...")
    output = replicate.run(slug, input=build_input(args))

    # Replicate returns a URL, a file-like object, or a list of them depending on model.
    url = output[0] if isinstance(output, (list, tuple)) else output
    url = getattr(url, "url", url)  # FileOutput -> .url on newer clients
    if not isinstance(url, str):
        sys.exit(f"unexpected output from Replicate: {output!r}")
    download(url, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
