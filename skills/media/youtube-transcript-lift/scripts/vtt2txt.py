#!/usr/bin/env python3
"""vtt2txt.py — collapse a (YouTube auto-caption) .vtt into clean plain text.

YouTube auto-captions use a "rolling window": each cue repeats the previous
line plus one new word, and inline <00:00:00.000><c> timing tags mark each
word. Naive stripping leaves massive duplication. This dedups by word position.

Usage:
    python3 vtt2txt.py in.vtt            > out.txt   # paragraph-ish text
    python3 vtt2txt.py in.vtt --keep-nl  > out.txt   # one cue line per line
"""
import re
import sys

TAG = re.compile(r"<[^>]+>")            # <c>, </c>, <00:00:01.234>
TS = re.compile(r"\d\d:\d\d:\d\d\.\d\d\d")  # cue timestamp lines
HEADER = re.compile(r"^(WEBVTT|Kind:|Language:|NOTE|STYLE|::cue)")


def clean(path: str, keep_nl: bool) -> str:
    seen: list[str] = []
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = TAG.sub("", raw).strip()
        if not line or TS.search(line) or HEADER.match(line) or "-->" in line:
            continue
        # drop consecutive duplicates (the rolling-window artefact)
        if seen and seen[-1] == line:
            continue
        seen.append(line)
    if keep_nl:
        return "\n".join(seen)
    # join into flowing text, re-split into sentence-ish paragraphs
    text = re.sub(r"\s+", " ", " ".join(seen)).strip()
    return re.sub(r"(?<=[.!?]) (?=[A-Z])", "\n\n", text)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("usage: vtt2txt.py in.vtt [--keep-nl]")
    sys.stdout.write(clean(args[0], "--keep-nl" in sys.argv) + "\n")
