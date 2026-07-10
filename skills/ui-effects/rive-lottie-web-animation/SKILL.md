---
name: rive-lottie-web-animation
category: ui-effects
description: >
  Embed a designer-authored Rive (.riv) state machine or dotLottie (.lottie)
  animation at runtime on the web and DRIVE it from code — fire triggers, flip
  booleans, push numbers, react to hover/scroll/click, and wire animation Events
  back to JS. Use when handing off a Rive/LottieFiles export into React, Next.js,
  Vue, or plain HTML and the static GIF/MP4 won't cut it because the motion must
  respond to user state. Covers the exact packages, constructor options, Fit/
  Alignment layout, input API, and teardown so the embed actually runs.
when_to_use:
  - You have a .riv or .lottie exported from Rive / LottieFiles and need it live in a web app
  - A designer built a state machine and you must trigger states from app logic (hover, click, form state)
  - You need an interactive hero, loader, toggle, cursor, or icon that reacts to user input, not a looping GIF
  - Wiring Rive Events (name + custom data) back into JS to trigger app behaviour
  - Choosing between @rive-app canvas vs webgl2 and @lottiefiles/dotlottie-web vs dotlottie-react
  - Fixing a Rive/Lottie embed that renders blurry, at 0x0, or ignores its state machine
when_not_to_use:
  - Hand-coding a bespoke SVG/canvas effect from scratch — use interactive-distortion or spectra-noise
  - A pure CSS/JS motion primitive with no design-tool file — use scroll-reveal-section or magnetic-cursor
  - Static poster or one-off art with no runtime interactivity — use canvas-design or algorithmic-art
  - Building the animation itself (authoring in the Rive editor) — this skill only covers the web runtime handoff
keywords:
  - rive
  - lottie
  - dotlottie
  - state-machine
  - web-animation
  - interactive-animation
  - react
  - canvas
  - webgl
  - trigger
  - useStateMachineInput
  - lottiefiles
  - runtime
  - handoff
  - motion
similar_to:
  - interactive-distortion
  - liquid-image
  - scroll-reveal-section
  - magnetic-cursor
inputs_needed: A .riv or .lottie file (from Rive editor / LottieFiles), the state-machine name and input names as defined by the designer, and a target framework (React/Next, Vue, or plain HTML).
produces: A working runtime embed — a canvas that plays the state machine and code that fires triggers / sets inputs / listens for Events, plus correct resize and cleanup.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Rive & dotLottie Web Animation Handoff

Take a motion designer's **Rive state machine** or **LottieFiles dotLottie** export and
make it *interactive on the web* — driven by real app state, not just autoplaying.

## When to use

Use this the moment a `.riv` or `.lottie` lands in your repo and the brief is "make it
react" (hover to play, click to fire, scroll to scrub, form-valid to celebrate). If you
only need a passive loop, a GIF/MP4 is cheaper — this skill is about the *inputs*.

## Prerequisites

- **Node + a bundler** (Vite / Next / Webpack) for the npm route, OR just a browser for the CDN route.
- **The file**: `.riv` (Rive) or `.lottie`/`.json` (Lottie). `.lottie` is the zipped dotLottie format — prefer it over raw `.json`.
- **The designer's names** — you cannot guess these. Get the exact **state machine name**
  and each **input name** (and its type: Trigger / Boolean / Number). In Rive these show in
  the editor's State Machine panel; in LottieFiles' state-machine editor they're the input IDs.
- Rive packages: `@rive-app/canvas` (2D, smaller) or `@rive-app/webgl2` (effects/blend modes);
  React: `@rive-app/react-canvas` / `@rive-app/react-webgl2`. dotLottie: `@lottiefiles/dotlottie-web`
  and `@lottiefiles/dotlottie-react`. All are published and current on npm.

> Pick **one** Rive renderer. Mixing `canvas` and `webgl2` in the same bundle doubles the WASM payload.

## Recipe 1 — Rive in plain HTML (CDN, fastest smoke test)

```html
<canvas id="rive" width="500" height="500"></canvas>
<script src="https://unpkg.com/@rive-app/canvas@2"></script>
<script>
  const r = new rive.Rive({
    src: "https://cdn.rive.app/animations/vehicles.riv",
    canvas: document.getElementById("rive"),
    autoplay: true,
    stateMachines: "bumpy",              // exact SM name from the designer
    layout: new rive.Layout({ fit: rive.Fit.Contain, alignment: rive.Alignment.Center }),
    onLoad: () => r.resizeDrawingSurfaceToCanvas(),  // REQUIRED for crisp HiDPI render
  });

  // Fire a Trigger input the moment you need it:
  document.getElementById("rive").addEventListener("click", () => {
    const inputs = r.stateMachineInputs("bumpy");   // array of inputs on that SM
    const trig = inputs.find(i => i.name === "bump");
    trig && trig.fire();
  });
</script>
```

Key API facts (verified against rive.app docs):
- `r.stateMachineInputs(name)` → array; each input has `.name`, `.value` (Boolean/Number), and `.fire()` (Trigger).
- `r.resizeDrawingSurfaceToCanvas()` — call in `onLoad` and on every window resize, else it renders blurry.
- `r.play()` / `r.pause()` / `r.cleanup()` for lifecycle.

## Recipe 2 — Rive in React / Next.js

```jsx
import { useRive, useStateMachineInput, Layout, Fit, Alignment } from "@rive-app/react-canvas";

const STATE_MACHINE = "Login Machine";

export function LoginMascot({ isFocused, isSuccess }) {
  const { rive, RiveComponent } = useRive({
    src: "/mascot.riv",
    stateMachines: STATE_MACHINE,
    autoplay: true,
    layout: new Layout({ fit: Fit.Cover, alignment: Alignment.Center }),
  });

  // One hook per input. Trigger => .fire(); Boolean/Number => .value = x
  const lookInput  = useStateMachineInput(rive, STATE_MACHINE, "isChecking"); // Boolean
  const winTrigger = useStateMachineInput(rive, STATE_MACHINE, "success");    // Trigger

  React.useEffect(() => { if (lookInput) lookInput.value = isFocused; }, [isFocused, lookInput]);
  React.useEffect(() => { if (isSuccess && winTrigger) winTrigger.fire(); }, [isSuccess, winTrigger]);

  return <RiveComponent style={{ width: 320, height: 320 }} />;
}
```

`useStateMachineInput(rive, stateMachineName, inputName, initialValue?)` returns `null` until
the file loads — always guard with `if (input)`. The `RiveComponent` owns its own canvas and
auto-resizes to its container, so give the container a real width/height (a 0x0 parent = invisible).

`Fit` values: `Cover, Contain, Fill, FitWidth, FitHeight, ScaleDown, None, Layout`.
`Alignment` values: `Center, TopLeft, TopCenter, TopRight, CenterLeft, CenterRight, BottomLeft, BottomCenter, BottomRight`.

### Listening to Rive Events (animation → app)

```jsx
import { EventType, RiveEventType } from "@rive-app/react-canvas";

React.useEffect(() => {
  if (!rive) return;
  const onEvent = (event) => {
    const d = event.data;
    if (d.type === RiveEventType.General) console.log("Rive fired:", d.name, d.properties);
  };
  rive.on(EventType.RiveEvent, onEvent);
  return () => rive.off(EventType.RiveEvent, onEvent);
}, [rive]);
```

## Recipe 3 — dotLottie state machine (LottieFiles)

```js
import { DotLottie } from "@lottiefiles/dotlottie-web";

const dotLottie = new DotLottie({
  canvas: document.querySelector("#lottie"),
  src: "/rating.lottie",
  autoplay: true,
  layout: { fit: "contain", align: [0.5, 0.5] },
  renderConfig: { autoResize: true, devicePixelRatio: window.devicePixelRatio },
});

dotLottie.addEventListener("load", () => {
  dotLottie.stateMachineLoad("rating-sm");   // state machine ID from the LottieFiles editor
  dotLottie.stateMachineStart();             // after start, pointer events route automatically
  dotLottie.stateMachineSetNumericInput("rating", 4);
  dotLottie.stateMachineSetBooleanInput("isHovered", true);
  dotLottie.stateMachineFireEvent("submit");
});
```

dotLottie SM methods (verified): `stateMachineLoad(id)`, `stateMachineStart()`, `stateMachineStop()`,
`stateMachineSetNumericInput(name, n)`, `stateMachineSetBooleanInput(name, b)`,
`stateMachineSetStringInput(name, s)`, `stateMachineFireEvent(name)`. React equivalent:
`<DotLottieReact src="/rating.lottie" autoplay />` from `@lottiefiles/dotlottie-react`, then grab
the instance via the `dotLottieRefCallback` prop and call the same methods.

## Rive vs dotLottie — which to hand off

- **Rive** — richer runtime state machines, nested inputs, data binding, custom Events with payloads,
  vector-native `.riv`. Best when interactivity is complex or the animation feeds app logic back.
- **dotLottie** — huge existing Lottie/After-Effects library, tiny files, simpler no-code state
  machines. Best when the asset already exists as Lottie or the interaction is light.

## Verify

- File loads: `onLoad` (Rive) / `"load"` event (dotLottie) fires — log inside it.
- Names match: `r.stateMachineInputs("SM").map(i => i.name)` (Rive) prints the real input list.
  A silent no-op almost always means a **misspelled state-machine or input name**.
- Crispness: HiDPI looks sharp only after `resizeDrawingSurfaceToCanvas()` (Rive) or
  `renderConfig.autoResize` + `devicePixelRatio` (dotLottie).
- Teardown: on unmount call `rive.cleanup()` / `dotLottie.destroy()` — confirm no WASM/GL leak in repeated mounts.

## Pitfalls

- **0x0 canvas** — Rive/dotLottie inherit the container size; a flex/grid parent with no intrinsic
  height renders nothing. Set explicit `width`/`height` or CSS on the container.
- **Guessed names** — inputs are string-keyed and case-sensitive. Wrong name = silent no failure. Always
  print the input list once during integration.
- **Firing before load** — calling `.fire()` / `stateMachineSetNumericInput` before the file loads is
  ignored. Gate every input write behind the load callback or the `rive`/instance being non-null.
- **Wrong renderer** — blend modes, masks, and mesh deforms need `@rive-app/webgl2`; `@rive-app/canvas`
  will drop them without warning. Ask the designer if the file uses those features.
- **Raw `.json` Lottie** — use the `.lottie` (dotLottie) export; it bundles assets + the state machine.
  A plain `.json` has the animation but not always the interactivity graph.
- **Not resizing on window resize** — Rive won't re-sharpen automatically; add a `resize` listener that
  re-calls `resizeDrawingSurfaceToCanvas()`.
- **Autoplay + reduced motion** — respect `prefers-reduced-motion`; start paused and only play on intent
  for decorative loops.
