---
name: audio-mastering-chain
category: media
description: >
  Master and finish a mix to a delivery-ready file with Matchering + ffmpeg. Match a rough mix
  to the tonal balance, RMS, peak and stereo width of a mastered reference track, then LOCK an
  exact platform loudness spec (-14 LUFS Spotify/YouTube/TikTok, -16 podcasts, -23 broadcast)
  and true-peak ceiling with a two-pass ffmpeg loudnorm finish, encoding WAV/MP3/M4A. Reach for
  it on "master this track", "make it sound like <reference song>", "match a commercial master",
  "finish my mixdown", "prep for Spotify/DSP delivery", or "hit -14 LUFS but sound mastered, not
  just normalised". More than loudnorm.
when_to_use:
  - "Master a rough mixdown so it sounds commercial, matched to a reference track you love"
  - "Finish a track to an exact DSP/broadcast spec (-14 / -16 / -23 LUFS + true-peak ceiling)"
  - "Make my song's tone, loudness and stereo width match a professionally mastered reference"
  - "Prep a jingle, podcast bed, or track for delivery to Spotify/Apple/YouTube"
  - "Batch-master a set of tracks to one reference so an EP/album sounds cohesive"
  - "The mix is fine but flat/quiet/dull — give it the polish a mastering engineer would"
when_not_to_use:
  - "Only need to hit a LUFS number with no tonal/reference match → use audio-loudness-ducking"
  - "Duck music under a voiceover or de-noise dialogue → use audio-loudness-ducking"
  - "Split a song into vocals/drums/bass stems first → use stem-separation"
  - "Generate the music/jingle itself from scratch → use music-generation-jingle"
  - "ffmpeg/python not installed yet on this machine → run media-toolchain-bootstrap first"
keywords: [matchering, mastering, master chain, loudnorm, lufs, true peak, reference master, tonal match, rms, stereo width, spotify delivery, dsp, ebu r128, finish mix, pcm24, ffmpeg audio, limiter, dbtp, audio finishing]
similar_to: [audio-loudness-ducking, stem-separation, music-generation-jingle, ffmpeg-cookbook, batch-transcode-encode, media-toolchain-bootstrap]
inputs_needed:
  - "Absolute path to the TARGET mix (WAV strongly preferred; MP3 works if ffmpeg is present)"
  - "For a reference match: absolute path to a REFERENCE track (a commercial master you want to sound like)"
  - "Desired delivery spec — target LUFS (default -14) and true-peak ceiling (default -1 dBTP)"
  - "Output format wanted (24-bit WAV master, 320k MP3, or 256k M4A/AAC)"
produces: A delivery-ready mastered audio file (reference-matched and locked to an exact LUFS / true-peak spec)
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Audio Mastering Chain

Two stages, one deliverable. **Matchering** matches your mix to a reference master's tonal
balance, RMS, peak and stereo width — the creative "make it sound like that record" step.
Then a two-pass **ffmpeg loudnorm** finish locks an exact platform LUFS + true-peak spec
and encodes the delivery file. Matchering gets the *character* right; loudnorm gets the
*number* right. Doing only one leaves the job half-done.

## When to use

You have a mixdown that is technically fine but doesn't sit next to commercial tracks — too
dull, too quiet, wrong low-end weight, narrow stereo image — and you have (or can grab) a
reference master in the same genre. Or you just need to finish a track to DSP spec and want
it to sound mastered, not merely normalised.

If you only need to hit a loudness number with no tonal reference, `audio-loudness-ducking`
is the lighter tool — this skill is for *mastering*, which needs a reference.

## Prerequisites (this Mac)

**Matchering** (Python 3.9 OK — classifiers list 3.8/3.9/3.10):

```bash
python3 -m pip install -U matchering imageio-ffmpeg
python3 -c "import matchering, imageio_ffmpeg; print('matchering', matchering.__version__ if hasattr(matchering,'__version__') else 'ok')"
```

Honest dependency notes:
- Matchering 2.0.6 pulls numpy, scipy, soundfile, **resampy** (needs numba) and statsmodels.
  On a fresh 3.9 the numba/resampy build can be slow; if it fails, the chain still runs the
  loudnorm finish without the reference match (it warns and continues).
- `soundfile`/libsndfile reads/writes WAV/FLAC natively. **MP3 input needs ffmpeg** on PATH;
  the helper supplies the portable `imageio-ffmpeg` binary automatically.
- No brew ffmpeg here — every ffmpeg call resolves the portable binary:

```bash
FF=$(python3 -c "import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())")
"$FF" -version | head -1
```

**Delivery specs** (integrated LUFS / true-peak / loudness-range):

| Target                          | I (LUFS) | TP (dBTP) | LRA |
|---------------------------------|----------|-----------|-----|
| Spotify / YouTube / TikTok / IG | -14      | -1        | 11  |
| Apple Podcasts / spoken word    | -16      | -1        | 11  |
| EBU R128 broadcast              | -23      | -1        | 7   |

Note: Spotify normalises loudness on playback, so master to -14 rather than slamming to
-8; a quieter, more dynamic master survives their downward normalisation better.

## Recipe 1 — Full chain in one command (recommended)

Matchering match → loudnorm finish → encode, all in one:

```bash
python3 scripts/master_chain.py /abs/mymix.wav /abs/master.wav \
  --reference /abs/reference_song.wav --lufs -14 --tp -1
```

- Output extension picks the codec: `.wav` → 24-bit PCM, `.mp3` → 320k, `.m4a`/`.aac` → 256k.
- Omit `--reference` to skip Matchering and just finish to spec (loudnorm two-pass only).
- `--no-finish` stops after Matchering (raw reference-matched 24-bit WAV, no loudness lock).
- It prints the measured input loudness and the target so you can sanity-check the move.

## Recipe 2 — Matchering only, in Python

The core call. Results are a list of format helpers — request 16- and 24-bit at once:

```python
import matchering as mg
mg.log(print)                       # enable logging; omit for silent
mg.process(
    target="/abs/mymix.wav",        # your rough mix
    reference="/abs/reference.wav", # the commercial master to sound like
    results=[
        mg.pcm24("/abs/master_24bit.wav"),   # keep for the loudnorm finish
        mg.pcm16("/abs/master_16bit.wav"),   # CD / general delivery
    ],
)
```

Only `pcm16` and `pcm24` are exported as result helpers. Matchering already brick-wall-
limits just under 0 dBFS, so the 24-bit WAV is a true master — you finish it to a LUFS
number next, you do not re-limit it.

Tune the engine with `mg.Config` when needed (all optional, sensible defaults):

```python
cfg = mg.Config(internal_sample_rate=44100, max_length=15*60)  # 15-min cap by default
mg.process(target=..., reference=..., results=[...], config=cfg)
```

Raise `max_length` for long-form audio; it caps processing at 15 minutes otherwise.

## Recipe 3 — Just the loudnorm finish (already have a master)

If a mastering engineer already gave you a master and you only need DSP spec, run the
two-pass loudnorm directly (this is what `master_chain.py` does with no `--reference`):

```bash
# Pass 1 — measure
"$FF" -i /abs/master.wav -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null - 2>&1 \
  | sed -n '/{/,/}/p'
# Pass 2 — apply the five measured_* values it printed, encode delivery
"$FF" -i /abs/master.wav -af \
loudnorm=I=-14:TP=-1:LRA=11:measured_I=-9.2:measured_TP=-0.3:measured_LRA=5.1:measured_thresh=-19.8:offset=-0.2:linear=true \
-ar 48000 -c:a pcm_s24le /abs/delivery.wav
```

Swap the five numbers for your Pass-1 output. `linear=true` applies flat, transparent gain
when the master already fits the target range (it should — it's mastered).

## Recipe 4 — Batch an EP to one reference (cohesive album)

```bash
REF=/abs/reference.wav
for f in /abs/album/*.wav; do
  out="/abs/album/mastered/$(basename "${f%.wav}").mp3"
  python3 scripts/master_chain.py "$f" "$out" --reference "$REF" --lufs -14
done
```

Using one reference for every track is what makes an EP feel like a single record.

## Verify

- **Loudness landed on spec** — re-measure the OUTPUT; `input_i` should be within ~0.5 LU of
  target and `input_tp` at or below the ceiling:
  ```bash
  "$FF" -i /abs/master.wav -af loudnorm=I=-14:TP=-1:print_format=json -f null - 2>&1 | sed -n '/{/,/}/p'
  ```
- **No clipping / no inter-sample peaks** — `input_tp` must be ≤ your TP (e.g. -1.0). If it
  reads positive after Matchering-only, that's why you run the loudnorm finish.
- **A/B against the reference** — solo-switch between your master and the reference at matched
  perceived level. Tone and low-end weight should sit in the same ballpark, not identical.
- **Mono-fold check** — sum to mono and confirm nothing hollow/phasey appears; Matchering
  widens toward the reference and an over-wide reference can thin your mono image.

## Pitfalls

- **Matchering is not a loudness spec tool.** It matches the *reference's* loudness, whatever
  that is — often hot. Always run the loudnorm finish to hit the DSP number precisely.
- **Reference quality is everything.** Garbage reference → garbage master. Use a genuinely
  well-mastered, same-genre track. A loud/harsh reference bakes loud/harsh into your track.
- **Feed a clean, un-clipped mix.** Matchering can't fix clipping or a bad mix; it matches
  spectral/dynamic *shape*. Leave headroom in the mix (peaks around -6 dBFS) before mastering.
- **Don't double-limit.** Matchering already limits near 0 dBFS. The loudnorm finish with
  `linear=true` is flat gain, not another limiter — do not stack a second `alimiter`.
- **MP3 target/reference needs ffmpeg.** Without ffmpeg on PATH, Matchering can't decode MP3;
  the helper's portable binary covers it, or convert to WAV first.
- **192 kHz surprise from loudnorm.** It resamples internally; always set `-ar 48000` (or
  44100) on the finish output — the helper does this for you.
- **Very short clips (< a few seconds)** give loudnorm an unreliable LRA read; for stings/
  idents, measure and trust `input_i` over `input_lra`.
- **resampy/numba install pain on 3.9** can block Matchering. The chain degrades to loudnorm-
  only with a warning rather than failing — but you lose the reference match, so fix the
  install (or use a venv with prebuilt wheels) if the tonal match matters.
