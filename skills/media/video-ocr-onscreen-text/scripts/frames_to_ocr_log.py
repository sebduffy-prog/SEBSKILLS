#!/usr/bin/env python3
"""OCR a folder of extracted frames, dedupe consecutive text, emit timecoded log + SRT.

Frames are expected to be named so they sort in playback order (e.g. f_000123.png).
Timecode for frame index i is i / --fps seconds. Extract frames at a known, EVEN fps
first (see SKILL.md), optionally cropped to the caption/lower-third band.

OCR backend, in order of preference on this Mac:
  --backend vision   Apple Vision via `ocrmac` (native, fast, no GPU). pip install ocrmac
  --backend paddle   PaddleOCR (heavier; supports many langs). pip install paddleocr

Outputs:
  <out>.csv  one row per distinct on-screen text block: start,end,text
  <out>.srt  same, as SubRip subtitles (for burned-in-subtitle rips)
"""
import argparse
import csv
import glob
import os
import sys


def tc(seconds, srt=False):
    """Seconds -> HH:MM:SS,mmm (srt) or HH:MM:SS.mmm."""
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    sep = "," if srt else "."
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def ocr_vision(path):
    from ocrmac import ocrmac
    anns = ocrmac.OCR(path, language_preference=None).recognize()
    # anns: list of (text, confidence, bbox); join lines top-to-bottom
    return " ".join(t.strip() for t, _c, _b in anns if t.strip())


def make_paddle(lang):
    from paddleocr import PaddleOCR
    engine = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def run(path):
        res = engine.ocr(path, cls=True)
        lines = []
        for block in (res or []):
            for _box, (text, _conf) in (block or []):
                if text.strip():
                    lines.append(text.strip())
        return " ".join(lines)

    return run


def similar(a, b):
    """Cheap similarity: treat as same caption if one contains the other or
    token overlap is high. Avoids re-logging jitter between near-identical frames."""
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    ta, tb = set(a.lower().split()), set(b.lower().split())
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    return inter / max(len(ta), len(tb)) >= 0.7


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("frames_dir", help="folder of frames sorted in playback order")
    ap.add_argument("--fps", type=float, required=True,
                    help="fps the frames were extracted at (e.g. 1 for 1/sec)")
    ap.add_argument("--out", default="onscreen_text", help="output basename")
    ap.add_argument("--backend", choices=["vision", "paddle"], default="vision")
    ap.add_argument("--lang", default="en", help="paddle lang code (en, ch, ...)")
    ap.add_argument("--glob", default="*.png", help="frame filename pattern")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.frames_dir, args.glob)))
    if not files:
        sys.exit(f"no frames matched {args.glob} in {args.frames_dir}")

    ocr = ocr_vision if args.backend == "vision" else make_paddle(args.lang)

    # Collect (index, text) then collapse runs of similar text into spans.
    rows = []  # dicts: start_i, end_i, text
    for i, f in enumerate(files):
        text = ocr(f) if args.backend == "vision" else ocr(f)
        text = " ".join(text.split())  # normalise whitespace
        if not text:
            continue
        if rows and similar(rows[-1]["text"], text):
            rows[-1]["end_i"] = i  # extend current span
        else:
            rows.append({"start_i": i, "end_i": i, "text": text})

    def start_s(r):
        return r["start_i"] / args.fps

    def end_s(r):
        # end of the last frame in the span = (end_i + 1) / fps
        return (r["end_i"] + 1) / args.fps

    with open(args.out + ".csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["start", "end", "text"])
        for r in rows:
            w.writerow([tc(start_s(r)), tc(end_s(r)), r["text"]])

    with open(args.out + ".srt", "w") as fh:
        for n, r in enumerate(rows, 1):
            fh.write(f"{n}\n{tc(start_s(r), True)} --> {tc(end_s(r), True)}\n{r['text']}\n\n")

    print(f"{len(rows)} distinct text blocks -> {args.out}.csv, {args.out}.srt")


if __name__ == "__main__":
    main()
