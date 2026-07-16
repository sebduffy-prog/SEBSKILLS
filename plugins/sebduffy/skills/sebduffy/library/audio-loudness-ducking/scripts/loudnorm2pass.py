#!/usr/bin/env python3
"""Two-pass EBU R128 loudnorm to an exact LUFS target.

Pass 1 measures the file; pass 2 applies the measurements for an accurate landing.
Video streams are stream-copied; only audio is re-encoded.

Usage:
    python3 loudnorm2pass.py /abs/in.mp4 /abs/out.mp4 [--i -14] [--tp -1] [--lra 11]
"""
import argparse
import json
import re
import subprocess
import sys


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"  # fall back to PATH


def measure(ff, src, i, tp, lra):
    """Run pass 1 and return the parsed loudnorm JSON block."""
    filt = f"loudnorm=I={i}:TP={tp}:LRA={lra}:print_format=json"
    proc = subprocess.run(
        [ff, "-hide_banner", "-i", src, "-af", filt, "-f", "null", "-"],
        stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True,
    )
    m = re.search(r"\{[^{}]*\}", proc.stderr, re.DOTALL)
    if not m:
        sys.exit("Pass 1 failed: no loudnorm JSON found.\n" + proc.stderr[-2000:])
    return json.loads(m.group(0))


def apply(ff, src, dst, i, tp, lra, stats):
    filt = (
        f"loudnorm=I={i}:TP={tp}:LRA={lra}"
        f":measured_I={stats['input_i']}"
        f":measured_TP={stats['input_tp']}"
        f":measured_LRA={stats['input_lra']}"
        f":measured_thresh={stats['input_thresh']}"
        f":offset={stats['target_offset']}"
        f":linear=true:print_format=summary"
    )
    cmd = [
        ff, "-hide_banner", "-y", "-i", src, "-af", filt,
        "-ar", "48000", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", dst,
    ]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit("Pass 2 failed.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--i", type=float, default=-14.0, help="integrated LUFS target")
    p.add_argument("--tp", type=float, default=-1.0, help="true-peak ceiling dBTP")
    p.add_argument("--lra", type=float, default=11.0, help="loudness range")
    a = p.parse_args()

    ff = ffmpeg_exe()
    print(f"[1/2] measuring {a.src} ...")
    stats = measure(ff, a.src, a.i, a.tp, a.lra)
    print(f"      input_i={stats['input_i']} input_tp={stats['input_tp']} "
          f"input_lra={stats['input_lra']}")
    print(f"[2/2] applying to hit I={a.i} TP={a.tp} ...")
    apply(ff, a.src, a.dst, a.i, a.tp, a.lra, stats)
    print(f"done -> {a.dst}")


if __name__ == "__main__":
    main()
