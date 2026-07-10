#!/usr/bin/env python3
"""Batch background removal + optional deck-prep (matte colour, square pad).

Run with uv so it uses Python 3.12 and an isolated env (this Mac's system
python3 is 3.9 and cannot run rembg):

  uv run --python 3.12 --with "rembg[cpu]" --with pillow \
      batch_cutout.py IN_DIR OUT_DIR [--model birefnet-general] \
      [--matte "#ffffff"] [--pad 1200] [--alpha-matting]

--matte    composite the cutout onto a solid colour (else transparent PNG)
--pad N    centre the result on an NxN square canvas (deck-consistent sizing)
Outputs are always .png. Existing outputs are skipped (resumable).
"""
import argparse
import sys
from pathlib import Path

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch cutout to transparent PNG.")
    p.add_argument("in_dir", type=Path)
    p.add_argument("out_dir", type=Path)
    p.add_argument("--model", default="birefnet-general",
                   help="rembg model (birefnet-general | bria-rmbg | isnet-general-use | u2net ...)")
    p.add_argument("--matte", default=None, help='solid bg colour e.g. "#ffffff" (else transparent)')
    p.add_argument("--pad", type=int, default=0, help="square canvas size in px (0 = keep bbox)")
    p.add_argument("--alpha-matting", action="store_true", help="cleaner edges on wispy subjects (slower)")
    return p.parse_args()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    if len(v) != 6:
        raise ValueError(f"--matte must be #rrggbb, got {value!r}")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def process_one(src: Path, dst: Path, session, args, Image, remove) -> None:
    with Image.open(src) as im:
        cut = remove(im.convert("RGBA"), session=session,
                     alpha_matting=args.alpha_matting)  # RGBA with real alpha

    if args.pad:
        cut = cut.crop(cut.getbbox() or (0, 0, cut.width, cut.height))
        side = args.pad
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        scale = min(side / cut.width, side / cut.height, 1.0) if max(cut.size) > side else 1.0
        if scale < 1.0:
            cut = cut.resize((max(1, int(cut.width * scale)), max(1, int(cut.height * scale))))
        canvas.alpha_composite(cut, ((side - cut.width) // 2, (side - cut.height) // 2))
        cut = canvas

    if args.matte:
        bg = Image.new("RGBA", cut.size, (*hex_to_rgb(args.matte), 255))
        bg.alpha_composite(cut)
        cut = bg

    dst.parent.mkdir(parents=True, exist_ok=True)
    cut.save(dst)


def main() -> int:
    args = parse_args()
    if not args.in_dir.is_dir():
        print(f"ERROR: input dir not found: {args.in_dir}", file=sys.stderr)
        return 2
    from PIL import Image
    from rembg import new_session, remove

    session = new_session(args.model)  # one session reused across the batch
    args.out_dir.mkdir(parents=True, exist_ok=True)

    srcs = sorted(p for p in args.in_dir.rglob("*") if p.suffix.lower() in EXTS)
    if not srcs:
        print(f"ERROR: no images in {args.in_dir}", file=sys.stderr)
        return 2

    done = failed = 0
    for src in srcs:
        dst = args.out_dir / src.relative_to(args.in_dir).with_suffix(".png")
        if dst.exists():
            continue
        try:
            process_one(src, dst, session, args, Image, remove)
            done += 1
            print(f"ok   {src.name} -> {dst}")
        except Exception as exc:  # keep the batch going, report at the end
            failed += 1
            print(f"FAIL {src.name}: {exc}", file=sys.stderr)

    print(f"\ndone={done} failed={failed} skipped={len(srcs) - done - failed} model={args.model}")
    return 1 if failed and not done else 0


if __name__ == "__main__":
    raise SystemExit(main())
