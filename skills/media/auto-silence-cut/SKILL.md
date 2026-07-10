---
name: auto-silence-cut
category: media
description: >
  Auto jump-cut talking-head, tutorial, podcast, or screen-recording footage by
  detecting and removing (or speeding up) the silent gaps — dead air, pauses,
  "umm" gaps — using auto-editor (with a pure-ffmpeg silencedetect fallback).
  Produces a tightened, punchier rendered video or an NLE timeline (Premiere /
  Resolve / Final Cut). Use when someone says "cut the silences", "remove dead
  air", "tighten this rambly video", "make my talking head snappier", "jump-cut
  my recording", "speed up the pauses", or "auto-edit this footage".
when_to_use:
  - Tighten a long, rambly talking-head or vlog by chopping out the pauses
  - Strip dead air and long gaps from a screen recording or tutorial
  - Speed up (rather than delete) silent stretches to keep continuity but save time
  - Auto jump-cut a podcast video before hand-polishing
  - Export cut points as a Premiere / Resolve / Final Cut timeline for non-destructive editing
when_not_to_use:
  - Just need burnt-in captions/subtitles → use whisper-caption-burn
  - Splitting one long video into topic shorts/clips → use long-video-to-shorts or video-clip-extractor
  - General re-encode / trim / concat with no silence analysis → use ffmpeg-cookbook
  - Reframing aspect ratio (16:9 → 9:16) → use social-video-reframe
  - Cutting on scene/shot changes rather than audio → use shot-scene-detection
keywords: [auto-editor, silence, jump-cut, dead air, silencedetect, talking head, remove silence, speed up silence, when-silent, margin, screen recording, podcast edit, tighten video, autoeditor, wyattblue, autocut]
similar_to: [ffmpeg-cookbook, shot-scene-detection, long-video-to-shorts, whisper-caption-burn, video-clip-extractor]
inputs_needed:
  - Path to the source video (or audio) file
  - Aggressiveness intent — cut vs speed-up silences, and how tight (threshold + margin)
  - Output intent — rendered video, or an NLE timeline (premiere/resolve/final-cut-pro)
produces: A tightened rendered video (default in_ALTERED.mp4) or an NLE timeline file
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Auto Silence Cut

Automatically remove or speed up the silent parts of talking-head, tutorial,
podcast, and screen-recording footage. Primary tool is **auto-editor**
(WyattBlue) — battle-tested, cross-NLE. A pure-ffmpeg `silencedetect` fallback is
bundled for when auto-editor won't install.

## When to use

Any "this video drags — cut the pauses" request. auto-editor analyses the audio
waveform, marks anything below a loudness threshold as silence, and either
deletes those spans or speeds them up, keeping A/V in sync automatically.

## Prerequisites

auto-editor 29.x requires Python >=3.9 (this Mac's 3.9 qualifies) and **bundles
its own ffmpeg** via `ae-ffmpeg` — no system ffmpeg needed for the primary path.

```bash
python3 -m pip install --user auto-editor
auto-editor --version      # expect 29.x
```

If the pip install fails (dependency/wheel issues on the old Python), use the
**ffmpeg fallback** (`scripts/silence_cut_ffmpeg.py`), which uses the portable
`imageio-ffmpeg` binary this machine already has:

```bash
python3 -m pip install --user imageio-ffmpeg   # if not present
```

## Recipes

All commands write a new file — the source is never modified.

### 1. Default cut (fast, sensible defaults)

```bash
auto-editor input.mp4                # -> input_ALTERED.mp4, silences removed
auto-editor input.mp4 -o tight.mp4 --no-open
```

`--no-open` stops it launching a player when done.

### 2. Tune the silence threshold

Two equivalent ways to say "how quiet counts as silence":

```bash
auto-editor input.mp4 --edit audio:threshold=4%      # percent of peak
auto-editor input.mp4 --edit audio:-19dB             # or a dB floor
```

Higher `%` / less-negative dB = more aggressive (cuts more). Start at `4%`
(~default), raise to `6-8%` for a noisy room, drop to `2-3%` for quiet speech.

### 3. Margin — keep breathing room around speech

Padding stops cuts sounding clipped. `before,after`:

```bash
auto-editor input.mp4 --margin 0.2s            # 0.2s both sides (default)
auto-editor input.mp4 --margin 0.1s,0.4s       # tighter in, looser out
```

### 4. Speed up silences instead of deleting them

Keeps continuity (good for screen recordings / demos) while saving time. Uses
the modern `--when-silent` / `--when-normal` action syntax (the old
`--silent-speed` / `--video-speed` still work but are deprecated):

```bash
# 8x through silence, normal-speed speech
auto-editor input.mp4 --when-silent speed:8

# also nudge speech to 1.3x for a snappier VO
auto-editor input.mp4 --when-silent speed:8 --when-normal speed:1.3
```

### 5. Screen recording with little/no speech — cut on motion

When there's no reliable voice track, edit on visual motion instead:

```bash
auto-editor screen.mp4 --edit motion:threshold=2%
# or combine: keep frames that are loud OR moving
auto-editor screen.mp4 --edit '(or audio:threshold=4% motion:threshold=2%)'
```

### 6. Export to an NLE (non-destructive)

Instead of rendering, emit a timeline with the cuts so you can polish by hand:

```bash
auto-editor input.mp4 --export premiere        # .xml for Premiere Pro
auto-editor input.mp4 --export resolve         # DaVinci Resolve
auto-editor input.mp4 --export final-cut-pro   # Final Cut Pro X
```

### 7. Pure-ffmpeg fallback (no auto-editor)

```bash
python3 scripts/silence_cut_ffmpeg.py input.mp4 tight.mp4 \
    --noise -30dB --min-silence 0.5 --pad 0.15 --min-clip 0.2
```

It runs `silencedetect`, inverts the silences into loud segments, pads/merges
them, then trims+concats in one `filter_complex` re-encode. `--noise` less
negative = more aggressive; `--pad` is the breathing room each side.

## Verify

- **Duration dropped:** compare before/after.
  ```bash
  for f in input.mp4 tight.mp4; do
    printf "%s " "$f"; python3 -c "import imageio_ffmpeg,subprocess,re,sys;\
b=imageio_ffmpeg.get_ffmpeg_exe();\
e=subprocess.run([b,'-i',sys.argv[1]],stderr=subprocess.PIPE,text=True).stderr;\
print(re.search(r'Duration: [\\d:.]+',e).group())" "$f"; done
  ```
- **Spot-check the seams:** play a few of the cut points — speech should not be
  clipped at word starts (if it is, widen `--margin` / `--pad`).
- **Sync intact:** confirm lips match audio at the end of the file, not just the
  start (drift means a re-encode issue, not a cut issue).

## Pitfalls

- **Over-aggressive threshold** eats quiet consonants/word tails → raise
  `--margin`, then lower the threshold. Tune margin before threshold.
- **Background hum/hiss** makes everything read as "loud" (nothing cut). Denoise
  first, or use a dB floor above the noise (e.g. `--edit audio:-25dB`).
- **auto-editor bundles ffmpeg** — do NOT assume it needs the system/portable
  binary. Only the fallback script uses `imageio-ffmpeg`.
- **Music/laughter under speech** counts as loud — silence cutting won't tighten
  those sections; that's expected.
- **Deprecated flags:** prefer `--when-silent speed:N` over `--silent-speed N`.
- **`--export`** produces a timeline, NOT a rendered video — you still open it in
  the NLE. Omit it to get a finished file.
- **Fallback re-encodes** (libx264/aac); for lossless-ish keep CRF low (18). It
  is slower and less clever than auto-editor — use it only when pip install fails.
