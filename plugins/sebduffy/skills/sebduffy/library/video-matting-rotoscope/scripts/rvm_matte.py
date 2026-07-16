#!/usr/bin/env python3
"""Temporally-stable human/portrait video matting with RobustVideoMatting (RVM).

Loads the pretrained RVM model + bundled converter straight from torch.hub
(no repo clone needed) and writes a green-screen composite, a raw alpha matte,
and the raw foreground. RVM carries a recurrent state across frames, so the
alpha is temporally coherent (no per-frame flicker) — unlike still-image
background removal run frame by frame.

Usage:
  python rvm_matte.py input.mp4 --variant mobilenetv3 \
      --downsample 0.25 --seq-chunk 12 \
      --composition com.mp4 --alpha pha.mp4 --foreground fgr.mp4

For an RGBA PNG sequence instead of green-screen video:
  python rvm_matte.py input.mp4 --png-sequence --composition out_rgba/

downsample-ratio guide (RVM's single most important knob):
  SD/512p ~0.4   HD/1080p ~0.25   4K ~0.125   (auto if omitted, but set it)
"""
import argparse
import os
import sys


def pick_device(requested: str) -> str:
    import torch
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        # RVM has ops that fall back to CPU on MPS; enable the fallback.
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        return "mps"
    return "cpu"


def main() -> int:
    p = argparse.ArgumentParser(description="RVM video matting")
    p.add_argument("input", help="input video file (or dir of frames)")
    p.add_argument("--variant", choices=["mobilenetv3", "resnet50"],
                   default="mobilenetv3", help="mobilenetv3=fast, resnet50=crisper edges")
    p.add_argument("--composition", help="output composite (green-screen mp4) or RGBA png dir")
    p.add_argument("--alpha", help="output raw alpha matte video/dir")
    p.add_argument("--foreground", help="output raw foreground video/dir")
    p.add_argument("--downsample", type=float, default=None,
                   help="downsample_ratio 0<r<=1 (HD~0.25, 4K~0.125); omit for auto")
    p.add_argument("--seq-chunk", type=int, default=12,
                   help="frames processed in parallel (higher=faster, more VRAM)")
    p.add_argument("--mbps", type=float, default=4.0, help="output bitrate for mp4")
    p.add_argument("--png-sequence", action="store_true",
                   help="write PNG/RGBA sequences instead of mp4 (paths become dirs)")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "mps", "cpu"])
    args = p.parse_args()

    if not (args.composition or args.alpha or args.foreground):
        p.error("give at least one of --composition / --alpha / --foreground")

    device = pick_device(args.device)
    import torch
    print(f"[rvm] device={device} variant={args.variant}", file=sys.stderr)

    model = torch.hub.load("PeterL1n/RobustVideoMatting", args.variant)
    convert_video = torch.hub.load("PeterL1n/RobustVideoMatting", "converter")
    # fp16 only helps on CUDA; keep fp32 on cpu/mps for correctness.
    dtype = torch.float16 if device == "cuda" else torch.float32
    model = model.to(device=device, dtype=dtype).eval()

    convert_video(
        model,
        input_source=args.input,
        output_type="png_sequence" if args.png_sequence else "video",
        output_composition=args.composition,
        output_alpha=args.alpha,
        output_foreground=args.foreground,
        output_video_mbps=args.mbps,
        downsample_ratio=args.downsample,   # None -> auto
        seq_chunk=args.seq_chunk,
        device=device,
        dtype=dtype,
        progress=True,
    )
    print("[rvm] done", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
