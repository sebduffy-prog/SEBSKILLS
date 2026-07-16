#!/usr/bin/env python3
"""Chatterbox few-shot voice-clone VO → single WAV.

Reads a script (text file or --text), splits it into sentence-ish chunks so
long narration stays coherent, generates each with the same reference clip,
and concatenates to one WAV at the model's native sample rate.

Usage:
  python3 clone_vo.py --ref ref10s.wav --in script.txt --out vo.wav
  python3 clone_vo.py --ref ref.wav --text "Hello there." --out hi.wav \
      --exaggeration 0.6 --cfg 0.4 --device mps

Needs a Python 3.11 venv:  pip install chatterbox-tts torch torchaudio
"""
import argparse, re, sys
import torch, torchaudio


def chunk(text, max_chars=280):
    # split on sentence boundaries, then pack up to ~max_chars per chunk
    parts = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    out, cur = [], ""
    for p in parts:
        if len(cur) + len(p) + 1 <= max_chars:
            cur = (cur + " " + p).strip()
        else:
            if cur:
                out.append(cur)
            cur = p
    if cur:
        out.append(cur)
    return [c for c in out if c.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="~10s clean reference WAV")
    ap.add_argument("--in", dest="infile", help="script text file")
    ap.add_argument("--text", help="inline text (overrides --in)")
    ap.add_argument("--out", default="vo.wav")
    ap.add_argument("--device", default=None, help="mps|cpu|cuda (auto if unset)")
    ap.add_argument("--lang", default=None, help="language_id for multilingual, e.g. fr")
    ap.add_argument("--exaggeration", type=float, default=0.5)
    ap.add_argument("--cfg", type=float, default=0.5)
    ap.add_argument("--max-chars", type=int, default=280)
    args = ap.parse_args()

    text = args.text or (open(args.infile, encoding="utf-8").read() if args.infile else None)
    if not text or not text.strip():
        sys.exit("No text: pass --text or --in <file>")

    dev = args.device or ("mps" if torch.backends.mps.is_available()
                          else "cuda" if torch.cuda.is_available() else "cpu")

    if args.lang:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS as M
        model = M.from_pretrained(device=dev)
        gen = lambda t: model.generate(t, audio_prompt_path=args.ref, language_id=args.lang,
                                       exaggeration=args.exaggeration, cfg_weight=args.cfg)
    else:
        from chatterbox.tts import ChatterboxTTS
        model = ChatterboxTTS.from_pretrained(device=dev)
        gen = lambda t: model.generate(t, audio_prompt_path=args.ref,
                                       exaggeration=args.exaggeration, cfg_weight=args.cfg)

    chunks = chunk(text, args.max_chars)
    print(f"device={dev} sr={model.sr} chunks={len(chunks)}", file=sys.stderr)
    wavs = []
    for i, c in enumerate(chunks, 1):
        print(f"[{i}/{len(chunks)}] {c[:60]}...", file=sys.stderr)
        wavs.append(gen(c))

    full = torch.cat([w.reshape(1, -1) for w in wavs], dim=1)
    torchaudio.save(args.out, full, model.sr)
    print(f"wrote {args.out} ({full.shape[1]/model.sr:.1f}s @ {model.sr}Hz)")


if __name__ == "__main__":
    main()
