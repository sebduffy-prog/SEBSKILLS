---
name: meeting-intelligence
category: documents
description: >-
  Turn a meeting recording or raw transcript into a clean deliverable pack: minutes,
  a decisions log, an owner/deadline action table, and ready-to-send follow-up email
  drafts. Use for standups, client calls, board meetings, interviews, or webinar recaps.
  Transcribes audio/video locally via Whisper when only a media file exists, then
  extracts structured, attributable, hallucination-guarded output. Trigger on "meeting
  notes", "minutes", "action items", "who owns what", "recap this call", "summarise
  this recording/transcript", or "follow-up email from this meeting".
when_to_use:
  - You have a recording (mp3/mp4/m4a/wav) or transcript and need structured minutes
  - Someone asks "who agreed to what and by when" from a call
  - You need owner + deadline action items pulled out of messy dialogue
  - You want follow-up / recap email drafts generated per stakeholder
  - You need a decisions log separated from discussion noise
when_not_to_use:
  - Live real-time captioning during a call (use a dedicated live-transcription app)
  - Pure audio cleanup/enhancement with no summarisation (use media_enhance_speech)
  - Formatting an already-written doc into Word/PDF (use docx or pdf skills)
  - Drafting a cold or unrelated email with no meeting source (use internal-comms)
keywords:
  - meeting minutes
  - action items
  - transcript
  - whisper
  - decisions log
  - follow-up email
  - recap
  - standup notes
  - speaker attribution
  - meeting summary
  - owner deadline
  - call notes
similar_to:
  - contract-review
  - internal-comms
  - doc-coauthoring
inputs_needed: A meeting recording (audio/video) OR a text transcript; optionally an attendee list, prior action items, and the meeting's stated agenda/goal.
produces: A markdown pack — meeting minutes, a decisions log, an owner/deadline action-item table, and per-stakeholder follow-up email drafts — plus a raw transcript if one was generated.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Meeting Intelligence

Convert a meeting into four attributable deliverables: **minutes**, a **decisions log**, an **owner/deadline action table**, and **follow-up email drafts**. Every extracted claim must trace back to the transcript — never invent decisions, owners, dates, or numbers that were not said.

## When to use

Use when the source is a real meeting (recording or transcript) and the caller wants structured, shareable output rather than a loose summary. If you only have audio/video, do Step 1 (transcribe) first; if you already have text, skip to Step 2.

## Prerequisites

- **Transcript path** given → no setup needed, go to Step 2.
- **Media file** given → you need `whisper` + `ffmpeg`. On this Mac (python3.9, no brew):
  - `python3 -m pip install --user openai-whisper` (pulls torch; first run downloads the model).
  - ffmpeg: use the imageio-ffmpeg binary already on this machine — `python3 -c "import imageio_ffmpeg,os,shutil;shutil.copy(imageio_ffmpeg.get_ffmpeg_exe(), os.path.expanduser('~/bin/ffmpeg'))"` then ensure `~/bin` is on `PATH`. Whisper shells out to an `ffmpeg` on `PATH`.
  - Apple-Silicon fast path (optional): `python3 -m pip install --user mlx-whisper` → `mlx_whisper audio.m4a --model mlx-community/whisper-large-v3-mlx`.

## Steps

### Step 1 — Transcribe (only if you were given a media file)

```bash
# base = fast/rough, small = good balance, medium/large = accurate but slow.
whisper "/path/meeting.m4a" \
  --model small \
  --language English \
  --output_format txt \
  --output_format srt \
  --output_dir "/path/out"
```

- Output: `out/meeting.txt` (clean text) and `out/meeting.srt` (timestamps — keep it; timestamps let you cite moments and disambiguate speakers).
- Whisper does **not** label speakers. If you need "who said what", either ask the user for the attendee list and infer turns conservatively, or run diarization separately (`pip install --user "whisperx"` for aligned diarization). Never guess a speaker's name onto a line you cannot attribute — mark it `[unattributed]`.
- Long file? Whisper handles hours in one pass but is slow on CPU; prefer `--model base` for a first look, then re-run `small`/`medium` if accuracy matters.

### Step 2 — Read the transcript and extract, grounded

Read the full transcript before writing anything. Then produce the pack below. Rules that keep it trustworthy:

- **Attribute or omit.** An action or decision needs a source in the text. If ownership/date was never stated, write `Owner: unassigned` / `Due: not stated` — do not fabricate.
- **Decisions vs discussion.** A *decision* is a settled commitment ("we'll ship Friday"). Open debate, options weighed, or "let's think about it" are **not** decisions — they belong in minutes, not the decisions log.
- **Preserve numbers verbatim.** Budgets, dates, metrics, names — copy exactly; never round or approximate.
- **Flag ambiguity** with `⚠︎` rather than resolving it silently (e.g. two people seemed to accept the same task).

### Step 3 — Emit the deliverable pack

Write to a markdown file (e.g. `out/meeting-pack.md`). Structure:

```markdown
# <Meeting title> — <date>
Attendees: <list, or "not stated">   ·   Duration: <hh:mm if known>

## 1. Minutes
- Concise, chronological or by-topic bullets of what was discussed.
- Include context needed to understand each decision/action.

## 2. Decisions Log
| # | Decision | Made by | Rationale (if stated) |
|---|----------|---------|-----------------------|
| 1 | ...      | ...     | ...                   |

## 3. Action Items
| # | Action | Owner | Due | Source quote |
|---|--------|-------|-----|--------------|
| 1 | ...    | Jane  | Fri 11 Jul | "I'll send the deck by Friday" |

## 4. Open Questions / Parking Lot
- Unresolved items, ⚠︎ ambiguities, follow-ups needed.

## 5. Follow-up Emails
### To: <owner / group>
Subject: <meeting> — your actions & recap
<2–5 sentence recap, then that person's action items with due dates, then a clear ask>
```

- One follow-up email **per owner** (or one group recap) so each person sees only what's theirs plus the shared summary.
- Keep emails send-ready: greeting, one-line recap, their bulleted actions with dates, a single clear next step, sign-off. No placeholders like `[insert]` left unfilled.

### Step 4 (optional) — Hand off to another format

- Word doc: pass the pack to the **docx** skill. PDF: the **pdf** skill. Calendar holds for deadlines: **Google_Calendar** `create_event`. Email delivery: **Gmail** `create_draft` (draft, don't auto-send).

## Verify

Before returning, self-check against the transcript:

- [ ] Every action item and decision has a locatable source in the text (spot-check 3 quotes).
- [ ] No owner/date/number appears that was not spoken (no fabrication).
- [ ] Decisions log contains only settled commitments, not open discussion.
- [ ] Each attendee with an assigned action has a follow-up email; unassigned actions are flagged, not hidden.
- [ ] Numbers, dates, and names are verbatim.
- Cheap grep sanity check on your own output vs source:
  ```bash
  # every name you assigned as an Owner should appear in the transcript
  grep -oE 'Owner: [A-Z][a-z]+' out/meeting-pack.md | sort -u
  ```

## Pitfalls

- **Whisper hallucinates on silence/music.** Long non-speech stretches produce repeated or invented lines. Skim the transcript; delete obvious loops before extracting.
- **No speaker labels from vanilla Whisper.** Do not assume the first speaker owns every action. Attribute only what the text supports; use `[unattributed]`.
- **Turning discussion into decisions.** The single most common error — "we could" / "maybe" / "let's explore" are NOT decisions. Be strict.
- **Rounding numbers.** "About 50k" stays "about 50k", not "$50,000". Copy figures exactly.
- **Over-long minutes.** Minutes summarise; they are not a re-transcription. If a bullet quotes more than a sentence, it's too long.
- **Auto-sending email.** Always produce drafts for human review; never send follow-ups directly.
- **Model too small for accuracy-critical calls.** `base` mangles names and figures. For legal/financial/board meetings use `medium` or `large` and still verify against audio.
- **ffmpeg not on PATH.** Whisper fails with a cryptic error if `ffmpeg` isn't callable; confirm `ffmpeg -version` works first.
