#!/usr/bin/env python3
"""Detect motion in a video (OpenCV MOG2 background subtraction) and emit
[start,end] time ranges of activity. Optionally cut them out with ffmpeg.

Usage:
  motion_clips.py cctv.mp4 [--min-area 800] [--sensitivity 25]
      [--pad 1.5] [--gap 1.0] [--min-dur 0.5] [--cut out_dir/]

Prints one "start end" pair per line (seconds). With --cut, also writes
a lossless-copy clip per range into out_dir/.

Deps: pip install opencv-python-headless numpy  (+ imageio-ffmpeg for --cut)
"""
import argparse
import subprocess
import sys
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:
    sys.exit("Install deps: pip install opencv-python-headless numpy")


def ffmpeg_bin() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def detect(video: str, min_area: int, sensitivity: int) -> tuple[list[bool], float]:
    """Return per-frame motion flags and fps."""
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        sys.exit(f"Cannot open {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    # varThreshold ~ sensitivity: lower = more sensitive. detectShadows off so
    # shadows don't register as motion.
    sub = cv2.createBackgroundSubtractorMOG2(
        history=500, varThreshold=sensitivity, detectShadows=False)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    flags: list[bool] = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        mask = sub.apply(frame)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)   # denoise
        mask = cv2.dilate(mask, kernel, iterations=2)           # merge blobs
        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        moved = any(cv2.contourArea(c) >= min_area for c in contours)
        flags.append(moved)
    cap.release()
    return flags, fps


def to_ranges(flags: list[bool], fps: float, gap: float, pad: float,
              min_dur: float) -> list[tuple[float, float]]:
    """Collapse motion frames into padded, gap-merged time ranges."""
    spans: list[list[float]] = []
    start = None
    for i, m in enumerate(flags):
        t = i / fps
        if m and start is None:
            start = t
        elif not m and start is not None:
            spans.append([start, t])
            start = None
    if start is not None:
        spans.append([start, len(flags) / fps])

    padded = [[max(0, s - pad), e + pad] for s, e in spans]
    merged: list[list[float]] = []
    for s, e in padded:
        if merged and s - merged[-1][1] <= gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged if (e - s) >= min_dur]


def cut(video: str, ranges: list[tuple[float, float]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fb = ffmpeg_bin()
    for i, (s, e) in enumerate(ranges):
        dest = out_dir / f"motion_{i:03d}_{s:.1f}-{e:.1f}.mp4"
        subprocess.run(
            [fb, "-hide_banner", "-loglevel", "error", "-y",
             "-ss", f"{s:.3f}", "-i", video, "-t", f"{e - s:.3f}",
             "-c", "copy", str(dest)],
            check=True,
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--min-area", type=int, default=800,
                    help="min contour px area to count as motion (default 800)")
    ap.add_argument("--sensitivity", type=int, default=25,
                    help="MOG2 varThreshold; lower=more sensitive (default 25)")
    ap.add_argument("--pad", type=float, default=1.5,
                    help="seconds of lead/tail padding per event (default 1.5)")
    ap.add_argument("--gap", type=float, default=1.0,
                    help="merge events closer than this many seconds (default 1)")
    ap.add_argument("--min-dur", type=float, default=0.5,
                    help="drop events shorter than this (default 0.5s)")
    ap.add_argument("--cut", metavar="OUT_DIR",
                    help="also write a clip per range with ffmpeg stream-copy")
    args = ap.parse_args()

    flags, fps = detect(args.video, args.min_area, args.sensitivity)
    ranges = to_ranges(flags, fps, args.gap, args.pad, args.min_dur)
    for s, e in ranges:
        print(f"{s:.3f} {e:.3f}")
    active = sum(e - s for s, e in ranges)
    print(f"# {len(ranges)} events, {active:.1f}s active / "
          f"{len(flags) / fps:.1f}s total", file=sys.stderr)
    if args.cut:
        cut(args.video, ranges, Path(args.cut))


if __name__ == "__main__":
    main()
