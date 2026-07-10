#!/usr/bin/env python3
"""Convert Whisper word-level timestamps into an animated karaoke .ass subtitle.

Input JSON (either shape is accepted):
  A) flat list:   [{"word": "hi", "start": 0.1, "end": 0.4}, ...]
  B) whisperx:    {"segments": [{"words": [{"word":"hi","start":0.1,"end":0.4}, ...]}]}
     (faster-whisper: dump each segment.words the same way)

Emits one Dialogue event PER WORD spanning that word's [start,end]. Every event
renders the whole caption chunk, with the active word popped bigger + accent-coloured
and the rest in the base colour. This gives the TikTok "current word lights up" look
without depending on \\k karaoke-timing quirks.

Usage:
  python words_to_ass.py words.json out.ass \
      --video-w 1080 --video-h 1920 \
      --max-words 4 --max-gap 0.6 \
      --font "Arial Black" --font-size 96 \
      --base "&H00FFFFFF" --accent "&H0000E0FF" --outline "&H00000000" \
      --margin-v 260

Colours are ASS BGR hex: &HAABBGGRR (AA=00 opaque). Default accent = warm yellow.
"""
import argparse, json, sys


def load_words(path):
    with open(path) as f:
        data = json.load(f)
    words = []
    if isinstance(data, dict) and "segments" in data:
        for seg in data["segments"]:
            words.extend(seg.get("words", []))
    elif isinstance(data, list):
        words = data
    else:
        sys.exit("Unrecognised JSON: need a list of words or {'segments':[...]}")
    out = []
    for w in words:
        txt = (w.get("word") or w.get("text") or "").strip()
        s, e = w.get("start"), w.get("end")
        if txt and s is not None and e is not None:
            out.append({"word": txt, "start": float(s), "end": float(e)})
    if not out:
        sys.exit("No usable words with start/end found (run with word_timestamps=True).")
    return out


def group(words, max_words, max_gap):
    """Break the word stream into caption chunks on word count or a silence gap."""
    chunks, cur = [], []
    for i, w in enumerate(words):
        if cur:
            gap = w["start"] - cur[-1]["end"]
            if len(cur) >= max_words or gap > max_gap:
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def ass_time(t):
    if t < 0:
        t = 0
    h = int(t // 3600); t -= h * 3600
    m = int(t // 60); t -= m * 60
    s = int(t)
    cs = int(round((t - s) * 100))
    if cs == 100:
        cs = 0; s += 1
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def esc(s):
    return s.replace("{", "(").replace("}", ")")


def build(chunks, a):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {a.video_w}
PlayResY: {a.video_h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{a.font},{a.font_size},{a.base},&H000000FF,{a.outline},&H64000000,-1,0,0,0,100,100,0,0,1,{a.outline_w},{a.shadow},2,60,60,{a.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text
"""
    lines = [header]
    pop = a.pop_scale
    for chunk in chunks:
        for i, w in enumerate(chunk):
            parts = []
            for j, cw in enumerate(chunk):
                token = esc(cw["word"])
                if j == i:
                    # active word: accent colour + scale pop that settles in 90ms
                    parts.append(
                        f"{{\\c{a.accent}\\fscx{pop}\\fscy{pop}"
                        f"\\t(0,90,\\fscx100\\fscy100)}}{token}{{\\r}}"
                    )
                else:
                    parts.append(token)
            text = " ".join(parts)
            start = ass_time(w["start"])
            # hold the active word until the next word begins (no flicker gaps)
            nxt = chunk[i + 1]["start"] if i + 1 < len(chunk) else w["end"]
            end = ass_time(max(w["end"], nxt))
            lines.append(
                f"Dialogue: 0,{start},{end},Cap,,0,0,0,,{{\\fad(60,60)}}{text}"
            )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("json"); p.add_argument("out")
    p.add_argument("--video-w", type=int, default=1080)
    p.add_argument("--video-h", type=int, default=1920)
    p.add_argument("--max-words", type=int, default=4)
    p.add_argument("--max-gap", type=float, default=0.6)
    p.add_argument("--font", default="Arial Black")
    p.add_argument("--font-size", type=int, default=96)
    p.add_argument("--base", default="&H00FFFFFF")
    p.add_argument("--accent", default="&H0000E0FF")
    p.add_argument("--outline", default="&H00000000")
    p.add_argument("--outline-w", type=float, default=4.0)
    p.add_argument("--shadow", type=float, default=0.0)
    p.add_argument("--margin-v", type=int, default=260)
    p.add_argument("--pop-scale", type=int, default=118)
    a = p.parse_args()
    chunks = group(load_words(a.json), a.max_words, a.max_gap)
    with open(a.out, "w") as f:
        f.write(build(chunks, a))
    nwords = sum(len(c) for c in chunks)
    print(f"wrote {a.out}: {len(chunks)} chunks, {nwords} words")


if __name__ == "__main__":
    main()
