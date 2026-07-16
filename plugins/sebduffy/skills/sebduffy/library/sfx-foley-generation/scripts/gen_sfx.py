#!/usr/bin/env python3
"""Generate a sound effect from a text prompt via ElevenLabs SFX v2.

Usage:
  ELEVENLABS_API_KEY=sk_... python3 gen_sfx.py "heavy wooden door creaks open" out.mp3 \
      --duration 4 --influence 0.5 --loop --format mp3_44100_128

Stdlib only (urllib) — no SDK required. Writes raw audio bytes straight to --out.
"""
import argparse, os, sys, json, urllib.request, urllib.error

API_URL = "https://api.elevenlabs.io/v1/sound-generation"
MODEL_ID = "eleven_text_to_sound_v2"
MIN_DUR, MAX_DUR = 0.5, 30.0


def main() -> int:
    p = argparse.ArgumentParser(description="ElevenLabs text-to-SFX")
    p.add_argument("text", help="Sound description prompt")
    p.add_argument("out", help="Output file (.mp3)")
    p.add_argument("--duration", type=float, default=None,
                   help=f"{MIN_DUR}-{MAX_DUR}s; omit to let the model auto-pick")
    p.add_argument("--influence", type=float, default=0.3,
                   help="prompt_influence 0-1 (default 0.3; higher = more literal)")
    p.add_argument("--loop", action="store_true", help="seamless loop")
    p.add_argument("--format", default="mp3_44100_128",
                   help="output_format, e.g. mp3_44100_128, pcm_44100, opus_48000_128")
    a = p.parse_args()

    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        print("ERROR: set ELEVENLABS_API_KEY", file=sys.stderr)
        return 2
    if a.duration is not None and not (MIN_DUR <= a.duration <= MAX_DUR):
        print(f"ERROR: --duration must be {MIN_DUR}-{MAX_DUR}", file=sys.stderr)
        return 2
    if not (0.0 <= a.influence <= 1.0):
        print("ERROR: --influence must be 0-1", file=sys.stderr)
        return 2

    body = {"text": a.text, "model_id": MODEL_ID,
            "prompt_influence": a.influence, "loop": a.loop}
    if a.duration is not None:
        body["duration_seconds"] = a.duration

    req = urllib.request.Request(
        f"{API_URL}?output_format={a.format}",
        data=json.dumps(body).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            audio = r.read()
    except urllib.error.HTTPError as e:
        print(f"ERROR {e.code}: {e.read().decode(errors='replace')}", file=sys.stderr)
        return 1
    if len(audio) < 1024:
        print(f"ERROR: suspiciously small response ({len(audio)} bytes)", file=sys.stderr)
        return 1
    with open(a.out, "wb") as f:
        f.write(audio)
    print(f"wrote {a.out} ({len(audio)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
