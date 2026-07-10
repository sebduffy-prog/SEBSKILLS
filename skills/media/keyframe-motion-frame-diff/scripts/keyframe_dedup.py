#!/usr/bin/env python3
"""Reduce a folder of frames (or a video) to unique keyframes via perceptual hash.

Usage:
  keyframe_dedup.py FRAMES_DIR --out unique/ [--threshold 6] [--hash phash]
  keyframe_dedup.py video.mp4  --out unique/ [--fps 2] [--threshold 6]

Consecutive-and-global dedup: a frame is kept only if its perceptual hash is
> threshold Hamming distance from EVERY already-kept keyframe. Lower threshold
= stricter (keeps more); typical 4-8 for phash(hash_size=8 -> 64-bit).

Deps: pip install pillow imagehash  (+ imageio-ffmpeg for video input)
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import imagehash
    from PIL import Image
except ImportError:
    sys.exit("Install deps: pip install pillow imagehash")

HASHERS = {
    "phash": imagehash.phash,      # DCT-based, robust to scaling/compression
    "dhash": imagehash.dhash,      # gradient, fast, good for near-dups
    "ahash": imagehash.average_hash,
    "whash": imagehash.whash,      # wavelet
}
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def ffmpeg_bin() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def extract_frames(video: Path, fps: float, workdir: Path) -> list[Path]:
    out = workdir / "frame_%06d.png"
    subprocess.run(
        [ffmpeg_bin(), "-hide_banner", "-loglevel", "error",
         "-i", str(video), "-vf", f"fps={fps}", str(out)],
        check=True,
    )
    return sorted(workdir.glob("frame_*.png"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="frames directory OR a video file")
    ap.add_argument("--out", required=True, help="output dir for kept keyframes")
    ap.add_argument("--threshold", type=int, default=6,
                    help="min Hamming distance to count as new (default 6)")
    ap.add_argument("--hash", choices=HASHERS, default="phash")
    ap.add_argument("--fps", type=float, default=2.0,
                    help="sample fps when src is a video (default 2)")
    args = ap.parse_args()

    src = Path(args.src)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    hasher = HASHERS[args.hash]

    tmp = None
    if src.is_dir():
        frames = sorted(p for p in src.iterdir() if p.suffix.lower() in IMG_EXTS)
    else:
        tmp = Path(tempfile.mkdtemp(prefix="kf_"))
        frames = extract_frames(src, args.fps, tmp)

    if not frames:
        sys.exit("No frames found.")

    kept: list[imagehash.ImageHash] = []
    kept_count = 0
    for i, fp in enumerate(frames):
        try:
            h = hasher(Image.open(fp))
        except Exception as e:  # noqa: BLE001
            print(f"skip {fp.name}: {e}", file=sys.stderr)
            continue
        if all((h - k) > args.threshold for k in kept):
            kept.append(h)
            dest = out_dir / f"key_{kept_count:05d}{fp.suffix.lower()}"
            shutil.copy2(fp, dest)
            kept_count += 1

    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"{len(frames)} frames -> {kept_count} unique keyframes "
          f"({args.hash}, threshold={args.threshold}) in {out_dir}")


if __name__ == "__main__":
    main()
