---
name: long-video-to-shorts
category: media
description: >
  Turn ONE long video (podcast, interview, webinar, lecture, stream VOD) into a ranked set of
  vertical 9:16 shorts — transcribe it, find and score the most clip-worthy moments (hooks,
  hot takes, quotable lines, story peaks), cut each into a 20-60s clip, face-track reframe to
  9:16, and burn captions. Produces ready-to-post TikTok/Reels/Shorts MP4s plus a ranked
  moments list. Use when someone says "cut this podcast into TikToks", "find the best moments
  for shorts", "chop my interview into clips", "make shorts from this webinar", or "what are
  the viral moments in this video".
when_to_use:
  - Cutting a long podcast, interview, or panel into multiple short vertical clips
  - "Find me the best/most viral moments" from a talk, stream, or webinar
  - Repurposing a lecture or keynote VOD into a batch of Reels/Shorts/TikToks
  - Getting a ranked shortlist of timestamped highlights before manually picking clips
  - Turning one horizontal source into many captioned 9:16 posts in one pass
when_not_to_use:
  - "You already know the exact in/out timecodes → use video-clip-extractor to just cut them"
  - "One clip is already cut, only need it vertical → use social-video-reframe"
  - "Only need burned-in captions on an existing clip → use whisper-caption-burn"
  - "Only want the raw transcript/subtitles, no clips → use youtube-transcript-lift or whisper-caption-burn"
  - "Removing dead air / tightening one talking-head clip → use auto-silence-cut"
  - "Splitting on camera cuts, not spoken moments → use shot-scene-detection"
keywords: [shorts generator, long video to shorts, podcast to tiktok, viral moments, highlight detection, clip finder, repurpose video, reels, shorts, tiktok clips, faster-whisper, 9:16, face tracking, opusclip, moment ranking, interview clips, webinar clips, chop podcast]
similar_to: [social-video-reframe, video-clip-extractor, whisper-caption-burn, auto-silence-cut, shot-scene-detection, youtube-transcript-lift]
inputs_needed:
  - Path to the long source video (or run youtube-download first)
  - How many shorts to produce (default 5) and target length (default 20-60s each)
  - Target aspect ratio (default 9:16) and whether to burn captions (default yes)
  - Optional theme/angle to bias moment selection (e.g. "AI takes", "funniest bits")
produces: A folder of ranked vertical captioned MP4 shorts + a moments.md shortlist with timecodes and hook lines
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Long Video to Shorts

Orchestrate one long video into a ranked batch of vertical shorts. Five stages:
**transcribe → rank moments → cut → reframe 9:16 → caption.** The ranking is done by
*you, the agent* reading the transcript — no external LLM API or key needed. Reframing and
captioning delegate to sibling skills so each stage stays best-in-class.

## When to use

Source is long and talky (podcast, interview, webinar, keynote, stream VOD) and the goal is
*several* social clips, not one. If you already have the timecodes, skip to
`video-clip-extractor`. If it's one clip that just needs to go vertical, use
`social-video-reframe`.

## Prerequisites

- **ffmpeg (this Mac):** no brew. Portable binary from pip `imageio-ffmpeg`:
  `FFMPEG=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")`
  (or the copy at `_research_bank/bin/ffmpeg`).
- **Transcription:** `python3 -m pip install --user faster-whisper` (local, no key; runs on
  CPU int8 on this Mac). `pip yt-dlp is dead here` — if the source is a URL, fetch it first
  with the `youtube-download` skill (standalone `yt-dlp_macos` binary + portable deno).
- **Reframe + captions:** handled by the `social-video-reframe` and `whisper-caption-burn`
  skills — no extra install here.

## Pipeline

### 1. Transcribe into rankable segments

```bash
python3 scripts/transcribe_segments.py input.mp4 --model small --out transcript
```

Prints `[mm:ss-mm:ss] text` lines to stdout and writes `transcript.json`
(`[{start,end,text}]`). Use `--model medium` for messy audio, `--lang en` to skip
auto-detect. For a >90-min source, `--model tiny` first to scout, then re-cut precisely.

### 2. Rank the moments (you do this — read the transcript)

Read `transcript.json` / the stdout lines and pick the N best self-contained moments. Score
each against these virality signals (adapted from AI-Youtube-Shorts-Generator's criteria):

- **Hook** — opens with a question, bold claim, or curiosity gap in the first ~3s
- **Emotional peak** — laughter, surprise, anger, vulnerability
- **Opinion bomb / hot take** — a spicy, contrarian, or quotable one-liner
- **Revelation / story peak** — a payoff, twist, or "here's what happened"
- **Standalone** — makes sense with zero prior context (critical for the feed)
- **Practical value** — a crisp tip, number, or how-to

Each clip should be **20-60s** and start on a clean sentence boundary. Snap the start a beat
*before* the hook line and the end just *after* the payoff (use adjacent segment
`start`/`end` values). Write the shortlist to `moments.md`:

```markdown
| # | start | end  | dur | hook line                              | why it pops        |
|---|-------|------|-----|----------------------------------------|--------------------|
| 1 | 12:04 | 12:49| 45s | "Everyone's wrong about remote work…"  | hot take + payoff  |
| 2 | 03:31 | 04:12| 41s | "The day we almost went bankrupt…"     | story peak         |
```

Rank best-first. If the user gave a theme ("funniest bits", "AI takes"), bias selection to it.

### 3. Cut each clip (lossless, fast)

Cut from the master using the timecodes. `-ss` before `-i` seeks fast; re-encode so cuts land
on exact frames (keyframe-copy can start on black):

```bash
FFMPEG=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
mkdir -p clips shorts
# per moment: start, end, index
$FFMPEG -ss 00:12:04 -to 00:12:49 -i input.mp4 \
  -c:v libx264 -crf 18 -preset veryfast -c:a aac -b:a 128k clips/01_raw.mp4
```

Batch straight from `moments.md` (columns: idx|start|end):

```bash
while IFS='|' read -r idx start end; do
  $FFMPEG -ss "$start" -to "$end" -i input.mp4 \
    -c:v libx264 -crf 18 -preset veryfast -c:a aac -b:a 128k "clips/${idx}_raw.mp4"
done < ranges.tsv   # e.g.  01<TAB>00:12:04<TAB>00:12:49
```

### 4. Reframe each clip to 9:16 (subject-aware)

Don't hand-roll the crop — use **`social-video-reframe`** (Tier 2 keeps an off-centre speaker
framed with no jitter):

```bash
for f in clips/*_raw.mp4; do
  python3 /path/to/social-video-reframe/scripts/smart_reframe.py \
    "$f" "shorts/$(basename "${f%_raw.mp4}")_9x16.mp4" --ar 9:16
done
```

Two speakers cutting back and forth → that skill's Tier 3 (dynamic pan) instead.

### 5. Burn captions

Reframe **before** captions so text is sized for the vertical frame. Then use
**`whisper-caption-burn`** on each `shorts/*_9x16.mp4` for word-timed karaoke-style subtitles
(big, high-contrast, safe-zone above the bottom nav). That skill re-transcribes each short
tightly, which is more accurate than slicing the long transcript.

## Verify

```bash
# Every short is vertical and the right length
for f in shorts/*_9x16.mp4; do
  $FFMPEG -hide_banner -i "$f" 2>&1 | \
    grep -Eo 'Duration: [0-9:.]+|[0-9]{3,4}x[0-9]{3,4}' | tr '\n' ' '; echo "  $f"
done
# expect ~1080x1920 (0.5625 = 9/16) and 20-60s durations
```

Spot-check clip #1: does it start on the hook, end on the payoff, keep the speaker in frame,
and make sense with no prior context? If not, nudge the `start`/`end` in `moments.md` and re-cut
that one — cutting is cheap.

## Pitfalls

- **Don't call an external LLM to rank.** You are the LLM — read `transcript.json` and score
  directly. Avoids keys, cost, and a dependency the repo needs but you don't.
- **Clips that need context flop.** The single biggest quality lever is *standalone*-ness. Drop
  a moment that references something 10 minutes earlier, however good the line.
- **Snap to sentence boundaries.** Starting mid-word or ending before the punchline lands kills
  it. Extend to the neighbouring segment's `start`/`end`, don't trim to the exact word.
- **Keyframe copy cuts drift.** `-c copy` starts on the nearest keyframe (often black/early).
  Re-encode (Stage 3) for frame-accurate in/out; it's fast at `-preset veryfast`.
- **Reframe THEN caption**, never the reverse — captioning a landscape file then cropping
  slices the text.
- **Whole-video transcript vs per-clip captions.** Use the long transcript only for *ranking*;
  let `whisper-caption-burn` re-transcribe each short for tight word timing.
- **Long sources:** transcription is O(length). Scout with `--model tiny`, and if the audio
  is >90 min consider `youtube-transcript-lift` (if a transcript already exists) to skip ASR.

## Sources

- [AI-Youtube-Shorts-Generator (SamurAIGPT)](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator) — virality-criteria ranking + local faster-whisper / OpenCV face-track pipeline this skill adapts.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — CTranslate2 local ASR.
