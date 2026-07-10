---
name: voiceover-dub-booth
category: recipes
description: >-
  Recreate an ElevenLabs / Chatterbox-style dubbing booth locally as a named combo — clone or
  preset-narrate a script into a voiceover, align it to the video's timing, sit it correctly in
  the mix by ducking the bed under speech, then mux a broadcast-clean dubbed track back onto the
  picture. Chain voice-clone-tts for the VO, whisper-caption-burn to align words to the script and
  timeline, audio-loudness-ducking to hit an exact LUFS target and sidechain-duck the music, and
  ffmpeg-cookbook to remux. Reach for this to dub or re-voice a clip, add narration, or replace a
  language track without paying per-character cloud TTS.
when_to_use:
  - You want an ElevenLabs/Chatterbox-style dub or re-voice of a video but done locally, no per-character billing
  - You need to add or replace a narration/voiceover track on existing footage and have it sit right in the mix
  - You are dubbing into another language or swapping the on-screen voice for a cloned/preset one
  - You need the new VO aligned to the picture (timed to shots/script) and loudness-correct for the target platform
  - You want a repeatable clone → align → duck → mux pipeline instead of a manual DAW session
when_not_to_use:
  - You only need the voiceover audio itself, no video or mixing → use voice-clone-tts alone
  - You only need on-screen captions/subtitles from speech → use whisper-caption-burn alone
  - You only need to fix levels / duck music on an existing mix → use audio-loudness-ducking alone
  - You only need to remux or swap an audio track on a video → use ffmpeg-cookbook alone
keywords:
  - voiceover
  - dubbing
  - dub booth
  - elevenlabs
  - chatterbox
  - tts
  - voice clone
  - narration
  - re-voice
  - lip sync
  - loudness
  - ducking
  - lufs
  - ffmpeg
  - mux
  - combo
  - local
similar_to:
  - voice-clone-tts
  - whisper-caption-burn
  - audio-loudness-ducking
  - ffmpeg-cookbook
inputs_needed: >-
  The source video (or a still + audio bed), the VO script text, and either a ~10s clean reference
  clip of the target voice (for cloning) or a chosen preset voice. A loudness target (e.g. -14 LUFS
  for social, -16 for podcast), plus a locally installed TTS model (Chatterbox / GPT-SoVITS / Kokoro),
  ffmpeg on PATH, and a scratch working dir.
produces: >-
  A dubbed video file with the new voiceover muxed onto the picture — VO timed to the script/shots,
  the music/ambience bed sidechain-ducked under speech, and the whole track normalised to the target
  LUFS. Plus the intermediate VO WAV and an optional aligned SRT/word-timing JSON.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Voiceover Dub Booth

Recreate a dubbing-studio workflow — clone a voice, narrate a script, drop it onto the picture in
time, and mix it so speech stays clear over the bed — entirely from local skills. This is the
open-source answer to an ElevenLabs dubbing project or a Chatterbox re-voice, chained from tools
that already live in this library.

## What it recreates

**ElevenLabs Dubbing / Chatterbox TTS + dubbing.** Those products take a script (or a source track),
generate a cloned or preset voiceover, time it to the video, and hand back a mixed, level-correct
dubbed file. This combo reproduces that pipeline locally: clone/narrate → align → duck → mux.

## Feasibility

**Rating: amber.** The *code path is green* — alignment (Whisper), loudness/ducking (ffmpeg
loudnorm + sidechain) and the mux (ffmpeg) all run fully locally with no key and no cloud.

The **amber step is step 1, voice-clone-tts**: the actual TTS/voice-clone model (Chatterbox,
GPT-SoVITS, or Kokoro) must be **installed and run locally**, and it is *not on this Mac out of the
box* — it needs a one-time model install (and ideally a GPU for speed; CPU works but is slow). That
single dependency is the only thing standing between this and a pure green recipe. Do not promise
instant output before the model is set up.

Honest boundary: this recreates the **audio dub**, not automatic lip-sync reanimation. The mouth
in the source footage will not be re-rendered to match the new words — matching is done by *timing
the VO to the cut*, the same as a traditional voiceover dub. If you need true visual lip-sync, that
is a separate video-generation problem outside this combo.

## The combo

An ordered chain. Each step names the exact sibling skill.

1. **voice-clone-tts** — generate the voiceover audio from the script: few-shot clone from a ~10s
   reference clip (Chatterbox / GPT-SoVITS) or a fast preset narrator (Kokoro). Emits the raw VO WAV.
   *(This is the amber step — model must be installed locally.)*
2. **whisper-caption-burn** — run Whisper on the generated VO to get **word-level timings**, and on
   the source (if it has speech) to find where lines land. Use those timings to align the VO to the
   script and the picture — this is the "align to script/timing" backbone, even when you never burn a
   caption. (It also gives you a free SRT if you want subtitles on the dub.)
3. **audio-loudness-ducking** — mix the VO against the bed: two-pass EBU R128 loudnorm to hit the
   exact platform LUFS target, and **sidechain-duck** the original music/ambience under the voiceover
   so speech stays intelligible. Optionally de-noise/de-hum the VO first.
4. **ffmpeg-cookbook** — **mux** the finished mixed audio back onto the video stream (map streams,
   `-c:v copy` to avoid re-encoding the picture), and stitch/trim if the dub changed the runtime.

## Prerequisites

- A **local TTS model installed** for step 1 — Chatterbox or GPT-SoVITS for cloning, Kokoro for a
  preset voice. This is the amber prerequisite; do the one-time setup before running the combo.
- **ffmpeg** on PATH (imageio-ffmpeg or the portable binary both work on this Mac — see the ffmpeg
  setup note in memory). Whisper available for step 2 (whisper-caption-burn handles the install).
- Inputs ready: source video, VO script, reference voice clip (for cloning) or chosen preset, and a
  loudness target for the destination platform.
- A scratch working dir for the VO WAV, timing JSON/SRT, mixed audio, and the output video.

## Run it

1. **Narrate.** Invoke **voice-clone-tts**: pass the script plus the ~10s reference clip (clone) or
   pick a preset voice. Generate the VO WAV. If the script is long or multi-line, generate per line
   so each can be nudged independently in the next step. Confirm the model is installed first.
2. **Align.** Invoke **whisper-caption-burn** on the VO WAV to get word-level timings; if the source
   has dialogue, transcribe it too to find each line's in-point. Build a timing map: which VO line
   sits at which timecode. Pad/trim silence between lines (ffmpeg `apad`/`atrim`) so the VO lands on
   the cut. Export an SRT here too if you want captions on the dub.
3. **Mix and duck.** Invoke **audio-loudness-ducking**: sidechain-duck the source music/ambience bed
   under the VO (speech ~ -14 to -16 LUFS integrated, bed dipping several dB under it), then run the
   two-pass loudnorm to the platform target. De-noise the VO first if the clone is hissy.
4. **Mux.** Invoke **ffmpeg-cookbook**: map the video stream from the source and the mixed audio from
   step 3 into the output (`-map 0:v -map 1:a -c:v copy -c:a aac -shortest`). If the dub changed the
   runtime, trim/concat the picture to match rather than letting audio and video drift.
5. **Deliver.** Write the dubbed MP4 (plus the VO WAV, timing JSON/SRT as byproducts).

## Verify

- Play the dubbed file end to end: every line lands on its shot, no VO spills past a cut, no dead air
  where a line should be.
- `ffprobe` the output — confirm one video + one audio stream, expected codecs, and runtime matches
  the picture (audio and video not drifting apart by the end).
- Re-measure integrated loudness (loudnorm print pass / an EBU R128 meter) and confirm it hits the
  target LUFS, and that true peak is under -1 dBTP.
- Listen with the bed under speech: the voiceover should stay clearly on top the whole time — if the
  music swells over a word, the ducking threshold/ratio needs tightening.
- If you cloned a voice, spot-check that it actually sounds like the reference and isn't robotic or
  clipping; regenerate the offending lines rather than EQ-patching them.

## Pitfalls

- **The amber step bites first.** If voice-clone-tts has no model installed, nothing downstream runs.
  Set up Chatterbox/GPT-SoVITS/Kokoro *before* starting, and expect slow generation on CPU-only.
- **VO length ≠ shot length.** Cloned lines rarely match the original line's duration. Align to the
  cut with silence padding/trimming (step 2) or gently time-stretch — never just paste and hope; that
  is what makes a dub feel off.
- **Ducking too aggressive or too soft.** Over-ducking pumps the music; under-ducking buries speech.
  Tune the sidechain threshold/ratio to the actual VO level, don't reuse a fixed preset blindly.
- **Loudness measured on the wrong signal.** Run loudnorm on the *final mixed* track, not the VO
  alone — the bed contributes to integrated loudness and true peak.
- **Re-encoding the picture needlessly.** Use `-c:v copy` in the mux; only re-encode video if you had
  to re-time it. Re-encoding costs quality for no reason on an audio-only change.
- **Overselling it as auto lip-sync.** This dubs the audio and times it to the cut; it does not
  reanimate mouths. Say so up front if the brief expects visual lip-sync.
- **Consent and likeness.** Cloning a real person's voice needs their permission — don't clone a voice
  you have no right to use.
