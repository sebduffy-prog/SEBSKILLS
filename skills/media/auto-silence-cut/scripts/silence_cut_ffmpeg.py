#!/usr/bin/env python3
"""Pure-ffmpeg fallback jump-cutter: detect silence, keep the loud bits.

Use ONLY when auto-editor is unavailable. Detects silence with ffmpeg
silencedetect, pads each kept (loud) segment, then trims+concats them back
into one file with a single filter_complex pass (re-encode, A/V in sync).

Usage:
  python silence_cut_ffmpeg.py IN.mp4 OUT.mp4 \
      [--noise -30dB] [--min-silence 0.5] [--pad 0.15] [--min-clip 0.2]

Notes:
- --noise: anything quieter than this counts as silence (less negative = more aggressive).
- --pad:   seconds of breathing room kept on each side of a loud segment.
- --min-clip: drop kept segments shorter than this (removes clicks/lip smacks).
"""
import argparse, os, re, subprocess, sys

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = "ffmpeg"


def probe_duration(path):
    out = subprocess.run([FFMPEG, "-i", path], stderr=subprocess.PIPE,
                         stdout=subprocess.DEVNULL, text=True).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", out)
    if not m:
        sys.exit("Could not read duration.")
    h, mn, s = m.groups()
    return int(h) * 3600 + int(mn) * 60 + float(s)


def detect_silences(path, noise, min_silence):
    out = subprocess.run(
        [FFMPEG, "-i", path, "-af",
         f"silencedetect=noise={noise}:d={min_silence}", "-f", "null", "-"],
        stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", out)]
    return list(zip(starts, ends))


def loud_segments(duration, silences, pad, min_clip):
    # Invert silence intervals into loud intervals, then pad + filter.
    keep, cursor = [], 0.0
    for s, e in silences:
        if s > cursor:
            keep.append((cursor, s))
        cursor = e
    if cursor < duration:
        keep.append((cursor, duration))
    padded = []
    for a, b in keep:
        a = max(0.0, a - pad)
        b = min(duration, b + pad)
        if b - a >= min_clip:
            padded.append((a, b))
    # Merge segments that overlap after padding.
    merged = []
    for a, b in padded:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def build_and_run(inp, out, segs):
    if not segs:
        sys.exit("No loud segments found — loosen --noise or lower --min-silence.")
    parts, concat = [], ""
    for i, (a, b) in enumerate(segs):
        parts.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}];")
        parts.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}];")
        concat += f"[v{i}][a{i}]"
    fc = "".join(parts) + f"{concat}concat=n={len(segs)}:v=1:a=1[v][a]"
    cmd = [FFMPEG, "-y", "-i", inp, "-filter_complex", fc,
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "18", "-c:a", "aac", "-b:a", "192k", out]
    subprocess.run(cmd, check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("inp"); p.add_argument("out")
    p.add_argument("--noise", default="-30dB")
    p.add_argument("--min-silence", type=float, default=0.5)
    p.add_argument("--pad", type=float, default=0.15)
    p.add_argument("--min-clip", type=float, default=0.2)
    a = p.parse_args()
    dur = probe_duration(a.inp)
    sil = detect_silences(a.inp, a.noise, a.min_silence)
    segs = loud_segments(dur, sil, a.pad, a.min_clip)
    kept = sum(b - x for x, b in segs)
    print(f"kept {len(segs)} segments, {kept:.1f}s of {dur:.1f}s "
          f"({100*kept/dur:.0f}%)", file=sys.stderr)
    build_and_run(a.inp, a.out, segs)


if __name__ == "__main__":
    main()
