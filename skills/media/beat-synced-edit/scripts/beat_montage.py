#!/usr/bin/env python3
"""Assemble a beat-synced montage: one clip per beat interval, cut to music.

Usage:
    python3 beat_montage.py --clips DIR_OR_FILES... --times times.txt \
        --music song.mp3 --out montage.mp4 [--size 1080x1920] [--fps 30]
        [--start-at SEC] [--max-clips N]

For each gap between consecutive beat times it takes the next clip, trims it to
that gap's duration (from the clip's own --start-at), scales/crops to --size,
then concatenates all segments and lays the original --music over the top.
Clips shorter than a gap are looped-then-trimmed. Requires ffmpeg + numpy.
"""
import argparse
import glob
import os
import subprocess
import sys
import tempfile

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}


def ffmpeg_exe():
    from shutil import which
    exe = which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{' '.join(cmd[:6])}...\n{p.stderr[-800:]}")


def gather_clips(patterns):
    out = []
    for pat in patterns:
        if os.path.isdir(pat):
            for f in sorted(os.listdir(pat)):
                if os.path.splitext(f)[1].lower() in VIDEO_EXT:
                    out.append(os.path.join(pat, f))
        else:
            out.extend(sorted(glob.glob(pat)))
    return [f for f in out if os.path.splitext(f)[1].lower() in VIDEO_EXT]


def read_times(path):
    with open(path) as fh:
        vals = [float(x) for x in fh.read().split() if x.strip()]
    if len(vals) < 2:
        sys.exit("Need at least 2 beat times to form 1 interval.")
    return vals


def main():
    ap = argparse.ArgumentParser(description="Beat-synced montage builder.")
    ap.add_argument("--clips", nargs="+", required=True,
                    help="Folder(s), file(s), or globs of source clips.")
    ap.add_argument("--times", required=True, help="File of beat times (one per line).")
    ap.add_argument("--music", required=True, help="Audio track laid over the cut.")
    ap.add_argument("--out", default="montage.mp4")
    ap.add_argument("--size", default="1080x1920", help="WxH (default vertical 9:16).")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--start-at", type=float, default=0.0,
                    help="Seconds into each clip to start the grab.")
    ap.add_argument("--max-clips", type=int, default=0,
                    help="Cap number of segments (0 = one per interval).")
    args = ap.parse_args()

    clips = gather_clips(args.clips)
    if not clips:
        sys.exit("No video clips found.")
    times = read_times(args.times)
    try:
        w, h = (int(x) for x in args.size.lower().split("x"))
    except ValueError:
        sys.exit("--size must look like 1080x1920")

    intervals = [(times[i + 1] - times[i]) for i in range(len(times) - 1)]
    intervals = [d for d in intervals if d > 0.02]
    if args.max_clips > 0:
        intervals = intervals[:args.max_clips]

    ff = ffmpeg_exe()
    workdir = tempfile.mkdtemp(prefix="beatmontage_")
    segs = []
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
          f"crop={w}:{h},fps={args.fps},setsar=1")
    for i, dur in enumerate(intervals):
        clip = clips[i % len(clips)]
        seg = os.path.join(workdir, f"seg_{i:04d}.mp4")
        # -stream_loop -1 lets short clips fill a long gap; -t caps the length.
        run([ff, "-y", "-stream_loop", "-1", "-ss", str(args.start_at),
             "-i", clip, "-t", f"{dur:.4f}", "-an",
             "-vf", vf, "-r", str(args.fps),
             "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
             seg])
        segs.append(seg)

    listfile = os.path.join(workdir, "concat.txt")
    with open(listfile, "w") as fh:
        for s in segs:
            fh.write(f"file '{s}'\n")
    silent = os.path.join(workdir, "silent.mp4")
    run([ff, "-y", "-f", "concat", "-safe", "0", "-i", listfile,
         "-c", "copy", silent])

    total = sum(intervals)
    run([ff, "-y", "-i", silent, "-i", args.music,
         "-map", "0:v:0", "-map", "1:a:0", "-t", f"{total:.4f}",
         "-c:v", "copy", "-c:a", "aac", "-shortest", args.out])
    print(f"Wrote {args.out}: {len(segs)} cuts, {total:.1f}s", file=sys.stderr)
    print(args.out)


if __name__ == "__main__":
    main()
