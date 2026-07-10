---
name: whisper-caption-burn
category: media
description: >
  Generate word-level Whisper captions and turn them into animated TikTok/Reels-style
  karaoke subtitles (active word pops + accent colour), then burn them into the video
  or soft-mux them as a toggleable track. Use when someone says "add TikTok captions",
  "burn subtitles into my reel", "word-by-word captions", "karaoke captions", "auto-caption
  this vertical video", "hardcode subtitles", or "add animated captions to social video".
  Covers faster-whisper / WhisperX transcription, styled .ass authoring, and the ffmpeg burn/mux.
when_to_use:
  - Adding TikTok/Reels/Shorts word-by-word captions where the current word highlights
  - Burning (hardcoding) subtitles into a vertical reel so they show without a caption track
  - Turning a Whisper transcript into a styled, animated .ass with brand colours and a bold font
  - Soft-muxing an SRT/ASS track a viewer can toggle on/off (delivery, not social)
  - Auto-captioning talking-head clips locally on this Mac with no cloud API
when_not_to_use:
  - Only need the plain transcript text or an SRT for a YouTube upload → use youtube-transcript-lift or a bare faster-whisper run
  - Reframing 16:9 to 9:16 / repositioning the subject → use social-video-reframe first, then caption
  - Cutting silences before captioning → run auto-silence-cut first
  - General ffmpeg filter/encode questions unrelated to subtitles → use ffmpeg-cookbook
  - Chopping a long video into captioned shorts → use long-video-to-shorts (it can call this per clip)
keywords: [captions, subtitles, whisper, faster-whisper, whisperx, ass, srt, karaoke, tiktok captions, word-level, burn-in, hardcode subtitles, subtitle burn, reels, shorts, force alignment, word timestamps, soft mux, animated captions]
similar_to: [ffmpeg-cookbook, social-video-reframe, auto-silence-cut, long-video-to-shorts, youtube-transcript-lift, stem-separation]
inputs_needed:
  - Path to the source video (and whether it is 9:16 vertical, 1:1, or 16:9 — sets caption position)
  - Style intent — burn-in (hardcoded) vs soft-mux (toggleable), plus font/accent colour if branded
  - Language (auto-detect is fine) and whether tight word alignment matters enough to use WhisperX
produces: A captioned .mp4 (burned or soft-muxed) plus the intermediate word-level .ass/.srt
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Whisper Caption Burn

Transcribe a clip with **word-level timestamps**, author an **animated karaoke `.ass`**
(active word pops + accent colour, TikTok/Reels style), then **burn** it into the pixels
or **soft-mux** it as a toggleable track — all local, no cloud.

## When to use

Talking-head reel, vertical explainer, or any social clip that needs on-screen captions
where the word being spoken lights up. If you only need flat text or a boring SRT, stop here
and use a plain transcript instead.

## Prerequisites (this Mac)

- **ffmpeg** — no brew here. Use the portable binary:
  `FF=$(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")`
  (also mirrored at `_research_bank/bin`). It is built **with libass**, required for the `ass`/`subtitles` filters — verify once: `"$FF" -filters | grep -E ' (ass|subtitles) '`.
- **Transcription** — install `faster-whisper` (CTranslate2 backend, ~4× faster than openai-whisper, CPU-friendly):
  `python3 -m pip install faster-whisper`. Do NOT reach for the `whisper` pip package or any cloud API.
- **Tighter alignment (optional)** — `WhisperX` (`pip install whisperx`) adds a wav2vec2 forced-alignment pass, snapping word times to <100 ms. Use it when the pop drifts off the voice; skip it for quick jobs.
- **Fonts** — libass resolves the `Fontname` from installed system fonts. "Arial Black" / "Impact" ship on macOS. For a brand font, install the `.ttf` (Font Book) or point ffmpeg at a dir with `fontsdir=`.
- Helper: `scripts/words_to_ass.py` (word JSON → animated `.ass`).

## Recipe A — faster-whisper → word JSON

```bash
python3 - "$VIDEO" <<'PY'
import sys, json
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")  # "medium"/"large-v3" if you have the RAM
segments, info = model.transcribe(sys.argv[1], word_timestamps=True, vad_filter=True)
words = [{"word": w.word, "start": w.start, "end": w.end}
         for seg in segments for w in seg.words]
json.dump(words, open("words.json", "w"))
print(f"lang={info.language} words={len(words)}")
PY
```

`vad_filter=True` drops silence so timestamps don't drift. Bump the model size for accuracy;
`int8` keeps it CPU-viable. ffmpeg extracts the audio internally — no separate WAV step needed.

### Recipe A′ — WhisperX when alignment must be tight

```bash
whisperx "$VIDEO" --model small --language en \
  --align_model WAV2VEC2_ASR_LARGE_LV60K_960H \
  --output_format json --output_dir .
# → <name>.json with {"segments":[{"words":[{"word","start","end"}...]}]}
```

`words_to_ass.py` reads that `{"segments":[...]}` shape directly — no reshaping.

## Recipe B — word JSON → animated karaoke .ass

```bash
python3 scripts/words_to_ass.py words.json captions.ass \
  --video-w 1080 --video-h 1920 \
  --max-words 4 --max-gap 0.6 \
  --font "Arial Black" --font-size 96 \
  --base "&H00FFFFFF" --accent "&H0000E0FF" \
  --outline "&H00000000" --outline-w 5 --margin-v 300 --pop-scale 120
```

- One `Dialogue` event **per word**; each renders the whole 4-word chunk with the spoken word
  scaled up (`\fscx/\fscy` settling via `\t`) and accent-coloured. That gives the reliable
  "current word lights up" look without `\k` timing fragility.
- Colours are **ASS BGR** `&HAABBGGRR` (AA=`00` opaque). `&H0000E0FF` ≈ warm yellow accent.
  A VCCP-magenta accent ≈ `&H00A80AE6`. Base white + black outline reads on any footage.
- `--margin-v` lifts captions above the TikTok UI (aim ~15–25% up from the bottom on 1920-tall).
- Chunks break on 4 words **or** a >0.6 s gap so lines never run long.
- Landscape? Pass `--video-w 1920 --video-h 1080 --font-size 64 --margin-v 90`.

## Recipe C — burn (hardcode) into the video

```bash
"$FF" -i "$VIDEO" \
  -vf "ass=captions.ass" \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \
  -c:a copy captioned.mp4
```

- Use the **`ass=`** filter (not `subtitles=`) for `.ass` — it honours the embedded styling/animation. `subtitles=` re-styles and can flatten it.
- `-c:a copy` keeps original audio. `-pix_fmt yuv420p` guarantees phone/Instagram compatibility.
- If the font isn't found, add a fonts dir: `-vf "ass=captions.ass:fontsdir=/Users/you/fonts"`.
- Filenames with spaces/colons inside a filtergraph must be escaped — safest is to `cd` next to the `.ass` and pass a bare basename, or wrap: `ass='my captions.ass'`.

## Recipe D — soft-mux (toggleable track, no re-encode)

```bash
# ASS as a selectable track (players that support ASS keep the styling)
"$FF" -i "$VIDEO" -i captions.ass -map 0 -map 1 \
  -c copy -c:s copy -disposition:s:0 default softsub.mp4

# Or a portable SRT track (universal, but loses animation/colour)
"$FF" -i "$VIDEO" -i captions.srt -map 0 -map 1 \
  -c copy -c:s mov_text -metadata:s:s:0 language=eng softsub.mp4
```

Soft-mux is for **delivery/QC** where the viewer toggles captions. Social platforms strip
sidecar tracks — for TikTok/Reels/Shorts you almost always want **Recipe C (burn-in)**.

## Verify

- `"$FF" -i captioned.mp4` — confirm the video stream re-encoded (burn) or a `Subtitle` stream exists (mux).
- Eyeball three frames where words change:
  `for t in 1 3 6; do "$FF" -ss $t -i captioned.mp4 -frames:v 1 -y frame_$t.png; done` — then open them and check the highlighted word matches the audio and sits clear of platform UI.
- Word count sanity: the script prints `chunks / words`; compare against `words.json` length.

## Pitfalls

- **No timestamps** → you forgot `word_timestamps=True`; the script exits with "No usable words".
- **Captions drift off the voice** → openai-whisper/faster-whisper word times can wobble; switch to Recipe A′ (WhisperX forced alignment).
- **Font ignored / wrong glyphs** → font not installed or ffmpeg built without libass. Verify libass (Prerequisites) and install the `.ttf` or use `fontsdir=`.
- **`subtitles=` vs `ass=`** → using `subtitles=` on an `.ass` drops your animation. Always `ass=` for styled ASS.
- **Green/black cast on Instagram** → missing `-pix_fmt yuv420p`.
- **Captions hidden behind TikTok UI** → raise `--margin-v`.
- **Reframe/silence-cut AFTER captioning** shifts every timestamp — always caption **last**, on the final-length, final-aspect cut.
- **`.mov` with odd audio** → add `-c:a aac -b:a 192k` instead of `copy` if `copy` errors on the source codec.
