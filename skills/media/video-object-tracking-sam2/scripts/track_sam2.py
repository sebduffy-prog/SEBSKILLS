#!/usr/bin/env python3
"""Track object(s) with SAM 2 / SAM 2.1 and write a binary mask PNG per frame.

Wraps SAM2VideoPredictor: build -> init_state -> add_new_points_or_box ->
propagate_in_video. Prompt on frame 0 with a box (x0,y0,x1,y1) or a point.

Run inside a Python >=3.10 env with sam2 installed (see SKILL.md). GPU/CUDA is
strongly preferred; MPS works with PYTORCH_ENABLE_MPS_FALLBACK=1 but is slow.

Example:
  python track_sam2.py --frames frames --out masks \
    --checkpoint sam2/checkpoints/sam2.1_hiera_small.pt \
    --config configs/sam2.1/sam2.1_hiera_s.yaml --box 420,180,610,430
"""
import argparse
import csv
import os
import sys

import numpy as np
import torch


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frames", required=True, help="dir of %05d.jpg frames, 0-indexed")
    p.add_argument("--out", required=True, help="output dir for mask PNGs")
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--config", required=True, help="e.g. configs/sam2.1/sam2.1_hiera_s.yaml")
    # Prompts are repeatable; each --box/--point can be paired with a preceding --obj.
    p.add_argument("--box", action="append", default=[], help="x0,y0,x1,y1 (repeatable)")
    p.add_argument("--point", action="append", default=[], help="x,y (repeatable)")
    p.add_argument("--label", type=int, default=1, help="1=foreground, 0=background (point)")
    p.add_argument("--obj", action="append", type=int, default=[], help="obj_id per prompt")
    p.add_argument("--frame", type=int, default=0, help="frame index to prompt on")
    p.add_argument("--boxes-csv", default="boxes.csv", help="write per-frame mask bbox here")
    p.add_argument("--offload", action="store_true", help="offload video+state to CPU (saves VRAM)")
    return p.parse_args()


def load_predictor(cfg: str, ckpt: str, device: str):
    from sam2.build_sam import build_sam2_video_predictor

    return build_sam2_video_predictor(cfg, ckpt, device=device)


def add_prompts(predictor, state, args) -> None:
    prompts = [("box", b) for b in args.box] + [("point", pt) for pt in args.point]
    if not prompts:
        sys.exit("error: supply at least one --box or --point prompt")
    for i, (kind, raw) in enumerate(prompts):
        obj_id = args.obj[i] if i < len(args.obj) else i + 1
        if kind == "box":
            box = np.array([float(x) for x in raw.split(",")], dtype=np.float32)
            predictor.add_new_points_or_box(
                inference_state=state, frame_idx=args.frame, obj_id=obj_id, box=box
            )
        else:
            pts = np.array([[float(x) for x in raw.split(",")]], dtype=np.float32)
            lbl = np.array([args.label], dtype=np.int32)
            predictor.add_new_points_or_box(
                inference_state=state, frame_idx=args.frame, obj_id=obj_id,
                points=pts, labels=lbl,
            )


def bbox_of(mask: np.ndarray):
    ys, xs = np.where(mask)
    if xs.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def main() -> None:
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)
    device = pick_device()
    print(f"device={device}", file=sys.stderr)
    if device == "mps":
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

    try:
        from PIL import Image
    except ImportError:
        sys.exit("error: pip install pillow")

    predictor = load_predictor(args.config, args.checkpoint, device)
    state = predictor.init_state(
        video_path=args.frames,
        offload_video_to_cpu=args.offload,
        offload_state_to_cpu=args.offload,
    )
    add_prompts(predictor, state, args)

    rows = []
    with torch.inference_mode():
        for frame_idx, obj_ids, mask_logits in predictor.propagate_in_video(state):
            # Union all objects into one binary mask per frame (>0 logit = in-mask).
            union = None
            for j in range(len(obj_ids)):
                m = (mask_logits[j] > 0.0).cpu().numpy().squeeze()
                union = m if union is None else np.logical_or(union, m)
            if union is None:
                continue
            Image.fromarray((union * 255).astype(np.uint8)).save(
                os.path.join(args.out, f"{frame_idx:05d}.png")
            )
            bb = bbox_of(union)
            if bb:
                rows.append((frame_idx, *bb))

    with open(args.boxes_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "x0", "y0", "x1", "y1"])
        w.writerows(rows)
    print(f"wrote {len(rows)} masks to {args.out} and {args.boxes_csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
