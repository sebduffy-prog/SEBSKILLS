#!/usr/bin/env python3
"""Detect beat (or onset) times in an audio/video file and print them.

Usage:
    python3 beat_times.py INPUT [--onsets] [--every N] [--offset SEC]
                          [--start-bpm BPM] [--tightness T] [--json]

INPUT may be audio (.wav/.mp3/.m4a/.flac) or video (.mp4/.mov/...); video
audio is extracted with ffmpeg first. Prints one time (seconds) per line,
or a JSON object with --json. Tempo is printed to stderr.

Grounded against librosa 0.11 (librosa.beat.beat_track / librosa.onset.onset_detect).
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}


def ffmpeg_exe():
    """Return an ffmpeg binary path (system, else the imageio_ffmpeg bundle)."""
    from shutil import which
    exe = which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # pragma: no cover - only when neither is present
        sys.exit(f"ffmpeg not found and imageio_ffmpeg unavailable: {e}")


def extract_audio(src):
    """Decode any container's audio to a temp 22050 Hz mono wav; return its path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    cmd = [ffmpeg_exe(), "-y", "-i", src, "-vn",
           "-ac", "1", "-ar", "22050", tmp.name]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        os.unlink(tmp.name)
        sys.exit(f"ffmpeg audio extraction failed:\n{proc.stderr[-800:]}")
    return tmp.name


def detect(path, onsets, start_bpm, tightness):
    """Return (tempo, [times]) using beat tracking or onset detection."""
    import librosa
    y, sr = librosa.load(path, sr=22050, mono=True)
    if onsets:
        frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
        times = librosa.frames_to_time(frames, sr=sr)
        tempo = 0.0
    else:
        import numpy as np
        tempo, frames = librosa.beat.beat_track(
            y=y, sr=sr, start_bpm=start_bpm, tightness=tightness)
        times = librosa.frames_to_time(frames, sr=sr)
        # beat_track returns tempo as a 1-element array; unwrap to a scalar.
        tempo = float(np.asarray(tempo).ravel()[0])
    return tempo, [round(float(t), 4) for t in times]


def main():
    ap = argparse.ArgumentParser(description="Detect beat/onset times.")
    ap.add_argument("input")
    ap.add_argument("--onsets", action="store_true",
                    help="Use transient onsets instead of the beat grid.")
    ap.add_argument("--every", type=int, default=1,
                    help="Keep every Nth beat (2=half-time, 4=downbeats).")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="Shift all times by SEC (align to a downbeat).")
    ap.add_argument("--start-bpm", type=float, default=120.0)
    ap.add_argument("--tightness", type=float, default=100.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"No such file: {args.input}")
    if args.every < 1:
        sys.exit("--every must be >= 1")

    ext = os.path.splitext(args.input)[1].lower()
    audio = args.input if ext in AUDIO_EXT else extract_audio(args.input)
    cleanup = audio != args.input
    try:
        tempo, times = detect(audio, args.onsets, args.start_bpm, args.tightness)
    finally:
        if cleanup and os.path.exists(audio):
            os.unlink(audio)

    times = [round(t + args.offset, 4) for t in times[::args.every]]
    print(f"tempo: {tempo:.1f} BPM  beats: {len(times)}", file=sys.stderr)
    if args.json:
        print(json.dumps({"tempo": tempo, "times": times}))
    else:
        print("\n".join(str(t) for t in times))


if __name__ == "__main__":
    main()
