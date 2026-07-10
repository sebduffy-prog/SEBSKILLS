#!/usr/bin/env python3
"""Multi-page contact-sheet / storyboard generator.

Wraps ffmpeg's fps + drawtext + tile filters. Splits a long video across
several numbered sheet pages (sheet-001.png, ...), burning the source timecode
onto each thumbnail. Uses the portable imageio-ffmpeg binary (this Mac has no
brew ffmpeg). No ffprobe needed — duration is parsed from ffmpeg stderr.

Usage:
  python3 contact_sheet.py IN.mp4 [--cols 5] [--rows 6] [--every N]
      [--width 320] [--out DIR] [--jpg] [--no-timecode] [--scene THRESH]

  --every N   one thumbnail per N seconds (drives how many pages are produced)
  --scene T   storyboard mode: sample scene cuts (thresh T), single page
  (omit --every and --scene) => one page, cols*rows thumbs spread over whole clip
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"imageio-ffmpeg not available ({exc}); pip install imageio-ffmpeg")


def probe_duration(ff: str, path: str) -> float:
    """Parse 'Duration: HH:MM:SS.ss' from ffmpeg stderr."""
    out = subprocess.run([ff, "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", out)
    if not m:
        sys.exit("Could not read duration from ffmpeg output.")
    h, mm, s = m.groups()
    return int(h) * 3600 + int(mm) * 60 + float(s)


def timecode_filter() -> str:
    return (
        f"drawtext=fontfile={FONT}:text='%{{pts\\:hms}}':x=6:y=h-th-6:"
        "fontcolor=white:fontsize=20:box=1:boxcolor=black@0.55:boxborderw=5"
    )


def count_scene_frames(ff: str, path: str, scene: float) -> int:
    """Count frames passing the scene-change filter (for a tight row count)."""
    res = subprocess.run(
        [ff, "-i", path, "-vf", f"select='gt(scene,{scene})'",
         "-an", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    m = re.findall(r"frame=\s*(\d+)", res.stderr)
    return int(m[-1]) if m else 0


def build_vf(cols: int, rows: int, width: int, fps: str,
             burn_tc: bool, scene: float | None) -> str:
    parts = []
    if scene is not None:
        parts.append(f"select='gt(scene,{scene})'")
    else:
        parts.append(f"fps={fps}")
    if burn_tc:
        parts.append(timecode_filter())
    parts.append(f"scale={width}:-1")
    parts.append(f"tile={cols}x{rows}:margin=8:padding=6:color=black")
    if scene is not None:
        parts.append("setpts=N/TB")
    return ",".join(parts)


def run_page(ff: str, src: str, ss: float, dur: float | None, vf: str,
             out_path: str, jpg: bool, scene: bool) -> None:
    cmd = [ff, "-y"]
    if ss > 0:
        cmd += ["-ss", f"{ss:.3f}"]
    cmd += ["-i", src]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-vf", vf, "-frames:v", "1", "-update", "1"]
    if scene:
        cmd += ["-vsync", "vfr"]
    if jpg:
        cmd += ["-q:v", "3"]
    else:
        cmd += ["-pix_fmt", "rgb24"]
    cmd += [out_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(out_path):
        sys.stderr.write(res.stderr[-1500:])
        sys.exit(f"ffmpeg failed for {out_path}")
    print(out_path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--rows", type=int, default=6)
    ap.add_argument("--every", type=float, help="one thumb per N seconds")
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--out", default="sheets")
    ap.add_argument("--jpg", action="store_true")
    ap.add_argument("--no-timecode", action="store_true")
    ap.add_argument("--scene", type=float, help="scene-cut threshold (0.2-0.4)")
    a = ap.parse_args()

    ff = ffmpeg_exe()
    os.makedirs(a.out, exist_ok=True)
    ext = "jpg" if a.jpg else "png"
    burn = not a.no_timecode
    per_page = a.cols * a.rows

    # Storyboard-by-scene: single page, rows sized to the actual cut count so
    # the sheet isn't padded with dozens of empty black rows.
    if a.scene is not None:
        n = count_scene_frames(ff, a.input, a.scene)
        if n == 0:
            sys.exit(f"No scene cuts above threshold {a.scene}; lower --scene.")
        rows = (n + a.cols - 1) // a.cols
        vf = build_vf(a.cols, rows, a.width, "", burn, a.scene)
        run_page(ff, a.input, 0, None,
                 vf, os.path.join(a.out, f"storyboard.{ext}"),
                 a.jpg, scene=True)
        return

    dur = probe_duration(ff, a.input)

    if a.every:  # fixed cadence -> as many pages as needed
        secs_per_page = per_page * a.every
        pages = max(1, int(dur // secs_per_page) + (1 if dur % secs_per_page else 0))
        fps = f"1/{a.every}"
        for p in range(pages):
            ss = p * secs_per_page
            page_dur = min(secs_per_page, dur - ss)
            if page_dur <= 0:
                break
            vf = build_vf(a.cols, a.rows, a.width, fps, burn, None)
            run_page(ff, a.input, ss, page_dur, vf,
                     os.path.join(a.out, f"sheet-{p + 1:03d}.{ext}"),
                     a.jpg, scene=False)
    else:  # single page spread over the whole clip
        fps = f"{per_page / max(dur, 0.001)}"
        vf = build_vf(a.cols, a.rows, a.width, fps, burn, None)
        run_page(ff, a.input, 0, None, vf,
                 os.path.join(a.out, f"sheet.{ext}"), a.jpg, scene=False)


if __name__ == "__main__":
    main()
