#!/usr/bin/env python3
"""Master + finish an audio track: Matchering (match a reference) -> ffmpeg
loudnorm (lock an exact platform LUFS/true-peak spec) -> encoded delivery file.

Runs on macOS Python 3.9. Uses the imageio-ffmpeg portable binary if no real
ffmpeg is on PATH. Every step is optional so it degrades gracefully:
  - no reference given  -> skip Matchering, just loudnorm-finish the target
  - matchering missing  -> skip Matchering with a warning, still finish
Nothing is mutated in place; a fresh WAV is written between stages.

Usage:
  master_chain.py TARGET OUT.wav|.mp3|.m4a [--reference REF] \
      [--lufs -14] [--tp -1] [--lra 11] [--no-finish]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TARGET_LUFS = -14.0   # YouTube / Spotify / TikTok / IG default
TARGET_TP = -1.0      # dBTP ceiling
TARGET_LRA = 11.0


def ffmpeg_bin():
    real = shutil.which("ffmpeg")
    if real:
        return real
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ERROR: no ffmpeg found. pip install imageio-ffmpeg, or install ffmpeg.")


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout


def matchering_stage(target, reference, out_wav):
    """Match tonal balance, RMS, peak and stereo width to the reference."""
    try:
        import matchering as mg
    except ImportError:
        print("WARN: matchering not installed; skipping reference match "
              "(pip install matchering). Finishing target directly.", file=sys.stderr)
        return target
    mg.log(lambda s: print(f"[matchering] {s}", file=sys.stderr))
    mg.process(
        target=target,
        reference=reference,
        results=[mg.pcm24(out_wav)],   # 24-bit master; finish stage encodes delivery
    )
    return out_wav


def measure(ff, src, lufs, tp, lra):
    """loudnorm pass 1 — measure the file, return the five measured_* fields."""
    code, out = run([ff, "-hide_banner", "-i", src, "-af",
                     f"loudnorm=I={lufs}:TP={tp}:LRA={lra}:print_format=json",
                     "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\}", out, re.S)
    if not m:
        sys.exit("ERROR: loudnorm measurement failed:\n" + out[-800:])
    return json.loads(m.group(0))


def finish_stage(ff, src, out, lufs, tp, lra):
    """loudnorm pass 2 — apply measured values, encode by output extension."""
    d = measure(ff, src, lufs, tp, lra)
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA={lra}:"
          f"measured_I={d['input_i']}:measured_TP={d['input_tp']}:"
          f"measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:"
          f"offset={d['target_offset']}:linear=true:print_format=summary")
    ext = os.path.splitext(out)[1].lower()
    codec = {".mp3": ["-c:a", "libmp3lame", "-b:a", "320k"],
             ".m4a": ["-c:a", "aac", "-b:a", "256k"],
             ".aac": ["-c:a", "aac", "-b:a", "256k"]}.get(ext, ["-c:a", "pcm_s24le"])
    code, log = run([ff, "-hide_banner", "-y", "-i", src, "-af", af,
                     "-ar", "48000", *codec, out])
    if code != 0:
        sys.exit("ERROR: loudnorm finish failed:\n" + log[-800:])
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("out")
    ap.add_argument("--reference")
    ap.add_argument("--lufs", type=float, default=TARGET_LUFS)
    ap.add_argument("--tp", type=float, default=TARGET_TP)
    ap.add_argument("--lra", type=float, default=TARGET_LRA)
    ap.add_argument("--no-finish", action="store_true",
                    help="stop after Matchering; do not loudnorm to spec")
    a = ap.parse_args()
    if not os.path.isfile(a.target):
        sys.exit(f"ERROR: target not found: {a.target}")

    ff = ffmpeg_bin()
    with tempfile.TemporaryDirectory() as tmp:
        stage_wav = a.target
        if a.reference:
            if not os.path.isfile(a.reference):
                sys.exit(f"ERROR: reference not found: {a.reference}")
            stage_wav = matchering_stage(a.target, a.reference,
                                         os.path.join(tmp, "matched.wav"))

        if a.no_finish:
            shutil.copyfile(stage_wav, a.out)
            print(f"DONE (match only) -> {a.out}")
            return

        d = finish_stage(ff, stage_wav, a.out, a.lufs, a.tp, a.lra)
        print(f"DONE -> {a.out}  (was {d['input_i']} LUFS / {d['input_tp']} dBTP, "
              f"targeted {a.lufs} LUFS / {a.tp} dBTP)")


if __name__ == "__main__":
    main()
