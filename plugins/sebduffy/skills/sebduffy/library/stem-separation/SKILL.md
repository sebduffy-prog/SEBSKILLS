---
name: stem-separation
category: media
description: >
  Split a song into separate stems — vocals, drums, bass, and other (or guitar/piano
  with the 6-source model) — using Demucs (Hybrid Transformer, htdemucs). On this Apple
  Silicon Mac take the MLX fast path (demucs-mlx, no PyTorch, a 7-min track in ~15s) or
  the classic PyTorch build with `-d mps`. Reach for this whenever someone says "get me
  an instrumental / karaoke version", "isolate the vocals for a remix / acapella",
  "remove the vocals from this track", "split this into stems", "extract just the drums
  or bassline", "give me a vocal-free backing track", or "source separation". Produces
  clean per-stem WAV/MP3 files, not a muddy EQ hack.
when_to_use:
  - "Make an instrumental / karaoke backing track by removing the vocals from a song"
  - "Isolate / extract the vocals (acapella) for a remix, sample, or mashup"
  - "Split a full mix into vocals + drums + bass + other stems"
  - "Pull out just the drum loop or the bassline from a finished track"
  - "Get a 6-stem split including guitar and piano"
  - "Clean up a stereo mix into components before re-mixing or ducking"
when_not_to_use:
  - "Just rip the whole audio track out of a video → use video-audio-rip"
  - "Normalise loudness / duck music under a VO / de-hiss dialogue → use audio-loudness-ducking"
  - "Cut silent gaps from a talking-head edit → use auto-silence-cut"
  - "Transcribe speech to text/captions → use whisper-caption-burn / youtube-transcript-lift"
  - "AI speech enhancement in the cloud → Adobe media_enhance_speech"
  - "Demucs / MLX / ffmpeg not installed yet → run media-toolchain-bootstrap first"
keywords: [demucs, stem separation, source separation, isolate vocals, remove vocals, instrumental, karaoke, acapella, backing track, htdemucs, htdemucs_ft, demucs-mlx, mlx, apple silicon, two-stems, drums bass vocals, remix stems, spleeter alternative, mps]
similar_to: [audio-loudness-ducking, video-audio-rip, ffmpeg-cookbook, whisper-caption-burn, auto-silence-cut, media-toolchain-bootstrap]
inputs_needed:
  - "Absolute path to the input song (any format ffmpeg reads: mp3, wav, m4a, flac, or a video file)"
  - "Which stems: all 4 (vocals/drums/bass/other), 6-source (adds guitar/piano), or just a 2-stem split (vocals vs no-vocals)?"
  - "Output format: WAV (lossless, default) or MP3 (smaller); and an output directory"
  - "Quality vs speed: fast MLX path, default htdemucs, or the slower fine-tuned htdemucs_ft"
produces: A folder of per-stem audio files (vocals.wav, drums.wav, bass.wav, other.wav — or an instrumental + vocals pair)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Stem Separation (Demucs)

Split a finished mix into isolated stems. Two engines: the **MLX fast path**
(`demucs-mlx`, native Apple Silicon, no PyTorch, ~10-15s for a full song) and the
**classic PyTorch Demucs** (broadest model support, `-d mps` for GPU). Both wrap the same
`htdemucs` model, so quality is identical — MLX is just faster to run on this Mac.

## When to use

Anytime the goal is *separating* an already-mixed track: instrumental/karaoke (drop the
vocals), acapella (keep only vocals), or a full 4/6-stem split for remixing. This is real
neural source separation, not a highpass/phase-cancel trick.

## Prerequisites (this Mac)

System `python3` is 3.9, but **both engines need Python ≥ 3.10** and pip-installing into
3.9 is unreliable here. Use `uv` (already at `~/.local/bin/uv`) to grab a modern
interpreter and run the tools in an isolated env — nothing touches system Python.

```bash
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.11        # one-time; no-op if already present
```

`ffmpeg` (for format conversion / muxing) is the portable `imageio-ffmpeg` binary:

```bash
FF=$(python3 -c "import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())")
```

First run of either tool downloads model weights (~80-350 MB) to a cache — needs network
once, then works offline. Always pass **absolute paths**.

## Recipe 1 — MLX fast path (recommended on this Mac)

`demucs-mlx` is a PyTorch-free port; a 7-minute song separates in ~12-15s.

```bash
# Full 4-stem split (vocals/drums/bass/other), WAV out
uvx --python 3.11 --from demucs-mlx \
  demucs-mlx -o "$HOME/Desktop/stems" "/abs/path/song.mp3"
# → $HOME/Desktop/stems/htdemucs/song/{vocals,drums,bass,other}.wav
```

`uvx` fetches `demucs-mlx` into a throwaway env and runs it — no manual venv. Add
`--list-models` to see options; `-n htdemucs_ft` for the fine-tuned (slower, marginally
cleaner) model; `--shifts 2` for a quality bump at ~2x time.

**Instrumental / acapella from the MLX split:** it outputs all 4 stems; build the two
products you actually want by summing:

```bash
D="$HOME/Desktop/stems/htdemucs/song"
# Instrumental = everything except vocals
"$FF" -y -i "$D/drums.wav" -i "$D/bass.wav" -i "$D/other.wav" \
  -filter_complex amix=inputs=3:normalize=0 "$D/instrumental.wav"
# Acapella is just vocals.wav (already isolated)
```

## Recipe 2 — Classic PyTorch Demucs (2-stem shortcut, 6-source, MPS)

The original `demucs` has a native `--two-stems` flag (writes just `vocals.wav` +
`no_vocals.wav` — the instrumental — directly, no manual mixdown) and the 6-source model.

```bash
# Karaoke/instrumental in one shot: vocals vs no_vocals, MP3 out, GPU via MPS
uvx --python 3.11 --from demucs \
  demucs --two-stems=vocals -d mps --mp3 --mp3-bitrate 320 \
  -o "$HOME/Desktop/stems" "/abs/path/song.mp3"
# → .../htdemucs/song/{vocals.mp3, no_vocals.mp3}

# 6 stems (adds guitar + piano)
uvx --python 3.11 --from demucs \
  demucs -n htdemucs_6s -o "$HOME/Desktop/stems" "/abs/path/song.wav"

# Highest quality 4-stem (fine-tuned model + 5 shifts, slow)
uvx --python 3.11 --from demucs \
  demucs -n htdemucs_ft --shifts 5 -d mps \
  -o "$HOME/Desktop/stems" "/abs/path/song.wav"
```

Key `demucs` flags: `-n <model>` (`htdemucs` default / `htdemucs_ft` / `htdemucs_6s` /
`mdx_extra`), `--two-stems=vocals`, `-o <dir>`, `--mp3 --mp3-bitrate 320`, `-d mps|cpu`,
`--shifts N` (quality), `-j 2` (parallel), `--int24`/`--float32`, `--segment N` (lower if
you hit memory limits on long tracks). Note `htdemucs_6s` does not support `--two-stems`.

Prefer this engine when you want the one-command instrumental (`--two-stems`), the 6-source
split, or a non-`htdemucs` model. Prefer MLX (Recipe 1) for raw speed on a plain 4-stem job.

## Recipe 3 — Separate a stem straight from a video

Demucs reads what ffmpeg reads, so point it at the video directly, or pre-extract:

```bash
"$FF" -y -i "/abs/path/clip.mp4" -vn -acodec pcm_s16le "/tmp/track.wav"
uvx --python 3.11 --from demucs-mlx demucs-mlx -o "$HOME/Desktop/stems" "/tmp/track.wav"
```

## Verify

```bash
D="$HOME/Desktop/stems/htdemucs/song"
ls -lh "$D"                         # expect vocals/drums/bass/other (non-zero sizes)
"$FF" -i "$D/vocals.wav" -f null -  # decodes cleanly; check duration ≈ source length
```

Then **listen**: play `vocals.wav` (should be near-dry voice) and the instrumental
(should have no lead vocal). Faint vocal "bleed" in the instrumental is normal —
`htdemucs_ft` + `--shifts` reduces it.

## Pitfalls

- **Wrong Python / pip-into-3.9 fails** → always launch via `uvx --python 3.11`. Do not
  `pip install demucs` into system 3.9.
- **First run "downloads" then seems to hang** → it's pulling model weights once; let it
  finish. Subsequent runs are offline and fast.
- **Out-of-memory on long tracks (PyTorch path)** → add `--segment 10` (or lower) and/or
  `-d cpu`. MLX handles long files with less RAM pressure.
- **`--two-stems` is Demucs-only** → `demucs-mlx` always emits all 4 stems; build the
  instrumental by mixing drums+bass+other (Recipe 1). And `htdemucs_6s` rejects
  `--two-stems`.
- **Output nested deeper than expected** → files land under `<out>/<model>/<trackname>/`,
  not directly in `<out>`. Trackname = input filename without extension.
- **Expecting a magically perfect acapella** → separation is excellent but not surgical;
  reverb tails and backing vox can smear. Set expectations for critical remix work.
- **Don't reach for this to just mute music under a VO or normalise levels** → that's
  `audio-loudness-ducking`. This tool is for pulling a mix apart into its instruments.
