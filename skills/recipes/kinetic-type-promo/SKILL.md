---
name: kinetic-type-promo
category: recipes
description: >-
  Recreate After-Effects-style kinetic typography and motion-graphics promos entirely web-native
  (CSS + WebGL, no AE) as a named combo. Chain motion-system for a shared timing vocabulary,
  text-scramble and svg-illustration-animation for animated type and vector reveals, spectra-noise
  for a living generative backdrop, then webapp-testing + ffmpeg-cookbook to screen-record the
  running page into a delivery MP4. Reach for this for a title card, lyric-style promo, launch teaser,
  or animated logo lockup you want reproducible in code instead of a timeline.
when_to_use:
  - You want an After-Effects-style kinetic-typography or motion-graphics promo but web-native (CSS/WebGL, no AE license)
  - You need a title card, lyric/quote reveal, product teaser, or animated logo lockup as a shareable MP4
  - The animation should be code-reproducible and re-editable (change copy, colours, timing) rather than baked in a timeline
  - You want one consistent motion feel (durations, easing, stagger) across type, vectors and backdrop
  - You need a repeatable render pipeline (run page → screen-record → encode) rather than a manual export
when_not_to_use:
  - You only need scrambling/decoding text on an existing page — use text-scramble alone
  - You only need one animated SVG illustration — use svg-illustration-animation alone
  - You just want a generative noise background with no type — use spectra-noise alone
  - You need true 3D camera moves, particles, or photoreal comps — that is outside the 2D/CSS/WebGL envelope (use a real 3D/AE pipeline)
  - You only need to encode/trim an existing video file — use ffmpeg-cookbook alone
keywords:
  - kinetic typography
  - motion graphics
  - after effects
  - promo
  - title card
  - lyric video
  - text animation
  - webgl
  - css animation
  - screen record
  - mp4
  - ffmpeg
  - generative backdrop
  - logo lockup
  - combo
  - web-native
similar_to:
  - motion-system
  - text-scramble
  - svg-illustration-animation
  - spectra-noise
  - webapp-testing
  - ffmpeg-cookbook
inputs_needed: >-
  The copy/headline (and any logo SVG), a colour palette, target aspect ratio and duration
  (e.g. 1920x1080, 10s), and desired mood/tempo. Node + a browser (Playwright via webapp-testing)
  and ffmpeg on PATH for the render step.
produces: >-
  A self-contained HTML/CSS/JS page that plays the kinetic-type promo in-browser, plus a rendered
  MP4 (and optional GIF/poster frame) of the sequence at the chosen resolution.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Kinetic Type Promo

Recreate the look of an After-Effects motion-graphics title sequence — animated headline type,
vector reveals, a living backdrop, all timed as one system — without ever opening After Effects.
Everything runs in the browser as CSS + WebGL and is captured to a delivery MP4 by chaining
skills that already exist in this library.

## What it recreates

Adobe After Effects / Premiere-style **kinetic typography and motion-graphics promos** (title cards,
lyric-video reveals, launch teasers, animated logo lockups). Here the "timeline" is code: the
sequence is authored in HTML/CSS/JS, plays deterministically in a browser, and is screen-recorded
into an MP4 for delivery.

## Feasibility

**Rating: green.** Fully reproducible locally within the **2D / CSS / WebGL envelope** — no AE,
no external model, no GPU cloud, no API key. Every step uses local skills, a headless browser and
ffmpeg on your machine.

Honest boundary: this recreates the *2D motion-graphics* look, not the whole of After Effects.
True 3D camera moves, volumetric particles, photoreal compositing, plugin effects (Element 3D,
Trapcode) are **out of scope** — do not oversell those. What lands convincingly: kinetic type,
stagger/scramble reveals, animated SVG strokes/fills, generative gradient/noise backdrops, and
smooth eased transitions.

## The combo

An ordered chain. Each step names the exact sibling skill.

1. **motion-system** — establish the shared timing vocabulary first: named duration/easing/spring/
   stagger tokens (CSS custom properties + a Motion JS map) plus a `prefers-reduced-motion` path.
   Everything below animates against these tokens so type, vectors and backdrop feel like one piece.
2. **text-scramble** — animate the headline/word reveals: decode/scramble-in the copy, per-character
   stagger, cycle between phrases. This is the primary "kinetic type" layer.
3. **svg-illustration-animation** — add animated vector elements: logo lockup stroke-draw, underline
   swipes, iconography, shape wipes. Handles the SVG path/stroke/fill motion the type layer can't.
4. **spectra-noise** — render the living backdrop: a WebGL generative noise/gradient field drifting
   behind the type so the frame never feels static (the motion-graphics "comp background").
5. **webapp-testing** — serve the page and drive it with Playwright: launch the dev server / open the
   HTML, trigger playback deterministically, and capture the animation window (screenshots per frame
   or a video capture) for the render.
6. **ffmpeg-cookbook** — encode the captured frames/video into the delivery MP4 at the target
   resolution and framerate (plus optional GIF and a poster frame).

## Prerequisites

- Node and a browser available for **webapp-testing** (Playwright).
- **ffmpeg** on PATH (see the YouTube/ffmpeg setup note in memory — imageio-ffmpeg or the portable
  binary both work on this Mac).
- Inputs ready: headline copy, optional logo SVG, palette, aspect ratio, duration, tempo/mood.
- A scratch working dir for the page, captured frames and the output MP4.

## Run it

1. **Lay the timing foundation.** Invoke **motion-system** to generate the token block
   (`--dur-*`, `--ease-*`, spring presets, stagger) as CSS variables + JS map. Decide the beat map:
   e.g. 0.0s backdrop in, 0.8s headline scramble, 2.5s logo draw, 8.0s hold, 9.5s out.
2. **Build the type layer.** Invoke **text-scramble** for the headline reveal(s), wiring its durations
   and stagger to the motion-system tokens (do not hand-pick random ms values).
3. **Add vectors.** Invoke **svg-illustration-animation** for the logo stroke-draw / underline / shape
   wipes, again driven by the shared tokens so they land on the same beats.
4. **Drop the backdrop.** Invoke **spectra-noise** for the WebGL noise/gradient field; set its palette
   to your brand colours and its speed to match the tempo. Layer it behind the type (z-index / canvas).
5. **Assemble one page.** Compose steps 2–4 into a single self-contained HTML file sized to the target
   canvas (e.g. a 1920x1080 stage), with a single JS timeline that fires each layer on its beat.
   Expose a `?record=1` or `window.play()` hook so playback can be triggered deterministically.
6. **Capture.** Invoke **webapp-testing**: serve/open the page, trigger `play()`, and capture the
   sequence — either frame-by-frame screenshots at a fixed fps (most deterministic) or a video capture
   of the stage element.
7. **Encode.** Invoke **ffmpeg-cookbook**: stitch frames (`-framerate N -i frame_%04d.png`) or transcode
   the capture into an H.264 MP4 at the target resolution/fps; optionally emit a GIF and a poster PNG.

## Verify

- Open the MP4 and confirm every beat lands: backdrop drift is smooth, headline scramble resolves
  cleanly, logo/vector reveals complete, no premature cut at the out point.
- Check the duration and resolution match the brief (`ffprobe` the file).
- Confirm no dropped/duplicated frames at the encode fps; if the capture stutters, raise the frame
  capture rate or slow the timeline, don't fake it in ffmpeg.
- Toggle `prefers-reduced-motion` and confirm the page still renders a sane static/attenuated version
  (motion-system's accessible path) — proves the sequence is genuinely token-driven.
- Sanity-check colours match the palette in the final MP4 (WebGL + video encode can shift gamma).

## Pitfalls

- **Timing drift between layers.** If each skill invents its own durations, the piece feels loose.
  Force every layer onto the motion-system tokens — that is why motion-system is step 1, not optional.
- **Non-deterministic playback.** CSS animations tied to wall-clock or `requestAnimationFrame` can
  desync from the capture. Prefer a driven timeline (seek to frame `t`) so screenshot capture is
  frame-exact; otherwise you get judder in the MP4.
- **WebGL backdrop capture.** Some headless capture paths miss WebGL canvases or capture them black.
  Verify spectra-noise actually appears in a webapp-testing screenshot before recording the full run;
  if black, enable the appropriate GPU/canvas flags or fall back to a CSS gradient backdrop.
- **Overselling AE parity.** This is 2D/CSS/WebGL. If the brief needs 3D camera, particles or plugin
  comps, say so up front — recreate the *look*, not the whole app.
- **Font loading race.** If web fonts load after playback starts, the first frames show fallback type.
  Preload fonts and gate `play()` on `document.fonts.ready`.
- **ffmpeg colour/gamma shift.** Encode with explicit `-pix_fmt yuv420p` and a sane colour matrix;
  eyeball the palette against the source page rather than trusting defaults.
