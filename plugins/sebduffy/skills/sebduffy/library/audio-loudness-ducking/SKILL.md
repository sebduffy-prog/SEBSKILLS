---
name: audio-loudness-ducking
category: media
description: >
  Fix audio levels the right way with ffmpeg: two-pass EBU R128 loudnorm to hit an exact
  platform target (-14 LUFS for YouTube/Spotify/TikTok/Instagram, -16 for podcasts, -23
  for broadcast), sidechain-duck background music under a voiceover so speech stays clear,
  and de-noise/de-hum a dialogue track (afftdn / highpass). Reach for this whenever someone
  says "normalise this reel to -14 LUFS", "my audio is too quiet / too loud", "make it pass
  loudness spec", "duck the music under the VO", "the music drowns out the voice",
  "clean up the hiss/hum", or "match the loudness across clips". Gives the exact two-pass
  measure-then-apply commands, not a vague single-pass loudnorm.
when_to_use:
  - "Normalise a reel/podcast/ad to an exact loudness target like -14 LUFS or -16 LUFS"
  - "My export got rejected / flagged as too loud or too quiet for the platform"
  - "Duck (auto-lower) background music whenever the voiceover is talking"
  - "The music is drowning out the narration — make speech sit on top"
  - "Clean up background hiss, hum, or air-conditioner noise on a dialogue track"
  - "Make several clips match each other in perceived loudness before stitching"
  - "Add a music bed under a VO and mix them properly"
when_not_to_use:
  - "Split a song into vocals/drums/bass stems → use stem-separation"
  - "Just rip the audio track out of a video file → use video-audio-rip"
  - "Cut silent gaps out of a talking-head edit → use auto-silence-cut"
  - "AI speech clean-up / enhancement in the cloud → Adobe media_enhance_speech"
  - "Any non-audio ffmpeg edit (concat, watermark, LUT, GIF) → use ffmpeg-cookbook"
  - "ffmpeg binary not installed yet → run media-toolchain-bootstrap first"
keywords: [loudnorm, lufs, ebu r128, loudness, normalize audio, normalise, -14 lufs, sidechain, ducking, sidechaincompress, duck music, voiceover, afftdn, denoise, de-hum, highpass, true peak, dynaudnorm, ffmpeg audio, integrated loudness, amix]
similar_to: [ffmpeg-cookbook, stem-separation, video-audio-rip, auto-silence-cut, whisper-caption-burn, batch-transcode-encode]
inputs_needed:
  - "Absolute path(s) to the input file(s) (video or audio)"
  - "For normalise: target LUFS (default -14) and true-peak ceiling (default -1 dBTP)"
  - "For ducking: the voiceover file AND the music file (separate), plus how hard to duck"
  - "For de-noise: is there a spot of noise-only audio to sample, or just apply adaptive?"
  - "Whether output is a media file (mux back to video) or a standalone audio file"
produces: A single output file with normalised loudness / ducked music / cleaned audio
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Audio Loudness & Ducking

Three jobs, one filter chain family. **Normalise** to an exact perceived-loudness target
(EBU R128 / ITU-R BS.1770), **duck** a music bed under speech, and **de-noise** dialogue.
All ffmpeg, all copy-pasteable.

## When to use

Audio that is too loud, too quiet, inconsistent between clips, has music fighting the
voice, or is hissy. The headline recipe is **two-pass loudnorm** — single-pass loudnorm
guesses and drifts; two-pass measures the file first, then applies exact correction and
actually lands on target.

## Prerequisites (this Mac)

No brew ffmpeg. Use the portable binary from `imageio-ffmpeg`:

```bash
FF=$(python3 -c "import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())")
"$FF" -version | head -1        # confirm it runs
```

Every recipe uses `"$FF"`. If a real `ffmpeg` is on PATH, use that instead. Always pass
absolute paths. `ffprobe` is NOT bundled — if you need it, it may be at
`_research_bank/bin/ffprobe`, else read stats from `$FF` stderr.

**Platform loudness targets** (integrated LUFS / true-peak ceiling):

| Target                         | I (LUFS) | TP (dBTP) | LRA |
|--------------------------------|----------|-----------|-----|
| YouTube / Spotify / TikTok / IG | -14      | -1        | 11  |
| Apple Podcasts / spoken word   | -16      | -1        | 11  |
| EBU R128 broadcast             | -23      | -1        | 7   |

## Recipe 1 — Two-pass normalise to an exact LUFS target

**Pass 1 — measure.** Analyse the file, print stats as JSON, discard output:

```bash
"$FF" -i /abs/in.mp4 -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null - 2>&1 \
  | sed -n '/{/,/}/p'
```

That prints a JSON block. Grab these five fields:
`input_i`, `input_tp`, `input_lra`, `input_thresh`, `target_offset`.

**Pass 2 — apply** those measurements as `measured_*` (this is what makes it exact and
enables `linear=true` single-shot gain instead of dynamic squashing):

```bash
"$FF" -i /abs/in.mp4 -af \
loudnorm=I=-14:TP=-1:LRA=11:measured_I=-19.3:measured_TP=-5.8:measured_LRA=6.4:measured_thresh=-29.7:offset=-0.4:linear=true:print_format=summary \
-ar 48000 -c:v copy -c:a aac -b:a 256k /abs/out.mp4
```

Swap the five numbers for your Pass-1 values. Notes:
- `-ar 48000` — loudnorm internally resamples to 192k; force a sane output rate or you get 192kHz audio.
- `-c:v copy` keeps the video untouched and only re-encodes audio. For an audio-only file drop it and write `.wav`/`.m4a`.
- `linear=true` applies flat gain (transparent) when the source fits the target LRA. If it can't, loudnorm falls back to dynamic mode automatically.

**One-shot script** (does both passes for you):

```bash
python3 scripts/loudnorm2pass.py /abs/in.mp4 /abs/out.mp4 --i -14 --tp -1 --lra 11
```

## Recipe 2 — Duck music under a voiceover (sidechain compression)

Two separate inputs: `voice` and `music`. Split the voice so it both triggers the
compressor (sidechain) and lands in the final mix. `sidechaincompress` on the music,
keyed by the voice, then `amix`:

```bash
"$FF" -i /abs/voice.wav -i /abs/music.mp3 -filter_complex \
"[0:a]asplit=2[vmix][vkey]; \
 [1:a][vkey]sidechaincompress=threshold=0.03:ratio=12:attack=20:release=350:makeup=1:level_sc=1[duck]; \
 [vmix][duck]amix=inputs=2:duration=longest:normalize=0[a]" \
-map "[a]" -c:a aac -b:a 256k /abs/mixed.m4a
```

Tuning:
- `threshold` (0–1 linear, not dB): lower = ducks more easily. 0.02–0.05 is typical for a VO.
- `ratio`: how deep the duck. 8–20. Higher = music drops further under speech.
- `attack` ms: how fast music ducks when voice starts (10–30 = snappy).
- `release` ms: how slowly music returns after voice stops (250–500 = smooth, no pumping).
- `normalize=0` on amix is important — the default `normalize=1` halves every input's gain.

Mix over a **video** (voice from the video, add a music bed and duck it):

```bash
"$FF" -i /abs/talk.mp4 -i /abs/music.mp3 -filter_complex \
"[0:a]asplit=2[vmix][vkey]; \
 [1:a][vkey]sidechaincompress=threshold=0.03:ratio=12:attack=20:release=350[duck]; \
 [vmix][duck]amix=inputs=2:duration=first:normalize=0[a]" \
-map 0:v -map "[a]" -c:v copy -c:a aac -shortest /abs/out.mp4
```

## Recipe 3 — De-noise / de-hum dialogue

**Adaptive (no sample needed)** — FFT denoiser plus a high-pass to kill rumble/handling:

```bash
"$FF" -i /abs/in.wav -af \
"highpass=f=80,afftdn=nr=12:nf=-25,alimiter=limit=0.95" \
/abs/clean.wav
```

- `highpass=f=80` removes low rumble, AC hum body, plosive thump.
- `afftdn nr` = noise reduction dB (10–20 sensible; too high = watery/robotic).
- `nf` = noise floor dB estimate; -25 is a good start, lower it for louder noise.

**Sample-based (stronger, when you have a noise-only region)** — use afftdn's noise
sampling via a timeline command. Simpler robust route: capture a noise print and let
afftdn track it with `-nt` off. In practice the adaptive chain above is enough for
reels; for heavy hiss, chain a mild second pass or use Adobe `media_enhance_speech`.

**Mains hum (50/60 Hz + harmonics)** — notch it:

```bash
"$FF" -i /abs/in.wav -af \
"anequalizer=c0 f=50 w=2 g=-30 t=1|c0 f=100 w=2 g=-30 t=1|c0 f=150 w=2 g=-25 t=1" \
/abs/dehum.wav
```

Use `f=60/120/180` in North America. Then run Recipe 1 to bring level back to target.

## Verify

- **Loudness landed on target** — re-measure the OUTPUT with a Pass-1 analysis; `input_i`
  should be within ~0.5 LU of your target and `input_tp` at or below the ceiling:
  ```bash
  "$FF" -i /abs/out.mp4 -af loudnorm=I=-14:TP=-1:print_format=json -f null - 2>&1 | sed -n '/{/,/}/p'
  ```
- **No clipping** — true peak (`input_tp`) must be ≤ your TP (e.g. -1.0). If it's positive, add `alimiter=limit=0.98` before output.
- **Ducking works** — listen at a voice-over-music boundary: music should audibly dip when speech starts and glide back in the gap, without pumping. If it pumps, raise `release`.
- **Video intact** — for muxed outputs confirm `-c:v copy` kept the stream: `$FF -i /abs/out.mp4 2>&1 | grep Video`.

## Pitfalls

- **Single-pass loudnorm misses target.** It normalises on the fly and drifts (often ±2 LU) and squashes dynamics. Always do two passes for delivery.
- **`threshold` in sidechaincompress is linear (0–1), not dB.** `threshold=0.03` ≈ -30 dB. Setting `threshold=-20` is invalid/ignored.
- **`amix` quietens everything by default.** `normalize=1` (default) scales each input by 1/N. Pass `normalize=0` and control levels with `volume`/`makeup` instead.
- **192 kHz surprise.** loudnorm upsamples internally; always set `-ar 48000` (or 44100) on output or downstream tools choke.
- **Mono/stereo mismatch** in ducking → add `aformat=channel_layouts=stereo` to each branch before amix.
- **Over-denoising** turns voices watery/underwater. Keep `afftdn nr` ≤ 20 and prefer a gentle highpass + mild reduction over one aggressive pass.
- **LRA too small to preserve.** If the source is heavily compressed already, `linear=true` can't hit both I and LRA and loudnorm silently switches to dynamic mode — that's fine, the target LUFS still lands.
