#!/usr/bin/env python3
"""Transcribe a long video/audio into compact timestamped segments for highlight ranking.

Emits BOTH:
  - <out>.json : list of {start, end, text} (machine-readable, for cutting)
  - stdout     : one line per segment "[mm:ss-mm:ss] text" (for the agent to rank)

Uses faster-whisper (CTranslate2) — fast, local, no API key, runs on this Mac.
Audio is extracted with the portable ffmpeg from pip imageio-ffmpeg.

Usage:
  python3 transcribe_segments.py input.mp4 [--model small] [--lang en] [--out transcript]
"""
import argparse, json, os, subprocess, sys, tempfile

def ffmpeg_bin():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        for p in ("_research_bank/bin/ffmpeg", "ffmpeg"):
            if os.path.exists(p) or p == "ffmpeg":
                return p
    return "ffmpeg"

def extract_wav(src, ff):
    wav = tempfile.mktemp(suffix=".wav")
    subprocess.run([ff, "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav

def ts(sec):
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--model", default="small", help="tiny|base|small|medium|large-v3 (default small)")
    ap.add_argument("--lang", default=None, help="language code, e.g. en (default: auto-detect)")
    ap.add_argument("--out", default="transcript", help="output basename (writes <out>.json)")
    args = ap.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("Install: python3 -m pip install --user faster-whisper")

    ff = ffmpeg_bin()
    wav = extract_wav(args.input, ff)
    try:
        model = WhisperModel(args.model, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(wav, language=args.lang, vad_filter=True)
        rows = []
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            rows.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": text})
            print(f"[{ts(seg.start)}-{ts(seg.end)}] {text}")
    finally:
        try: os.remove(wav)
        except OSError: pass

    with open(f"{args.out}.json", "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\n# {len(rows)} segments -> {args.out}.json", file=sys.stderr)

if __name__ == "__main__":
    main()
