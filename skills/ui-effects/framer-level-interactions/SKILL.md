---
name: framer-level-interactions
category: ui-effects
description: >
  Build Framer-grade interactive section components for marketing pages,
  product sites, portfolios, and dashboards. The skill covers seven
  battle-tested interaction recipes — 3D-tilt cards with cursor
  spotlight, magnetic CTA buttons, aurora-drift hero gradients,
  IntersectionObserver-eased number counters, sparkline draw-in charts,
  IntersectionObserver-sentinel infinite feeds, and Stripe/Apple-style
  sticky-scroll storytelling. Each pattern is plain React + inline
  styles + CSS-variable theme tokens — no Framer Motion or other heavy
  deps. Use this skill ANY time the user asks for "Framer-level" /
  "Linear-level" / "Stripe-level" / "Vercel-level" interactions, or
  says the site feels "flat" / "static" / "needs life" / "needs polish",
  or asks for specific moves (3D tilt, spotlight follow, magnetic
  button, animated counter, scrollytelling, sticky scroll, drawn-on
  chart, lazy / infinite feed). Trigger even if the user only names one
  pattern — the others belong together. SKIP only if the user
  explicitly asks for a pure-CSS or pure-server-rendered page with no
  client interactivity.
when_to_use:
  - User asks for "Framer-level", "Linear-level", "Stripe-level", or "Vercel-level" interactions on a page
  - A marketing page, portfolio, product preview, or dashboard feels "flat", "static", or "needs life / polish"
  - User asks for a specific move — 3D tilt, cursor spotlight, magnetic button, animated counter, scrollytelling, sticky scroll, drawn-on chart, or lazy/infinite feed
  - Building a hero section that needs an aurora-drift background plus a magnetic CTA
  - A stats strip needs IntersectionObserver-eased counters or sparkline draw-in charts
  - A long feed or grid needs sentinel-based infinite loading with staggered reveal
  - Composing several interaction patterns together on one section page (they layer, 3+ per page)
when_not_to_use:
  - User explicitly wants a pure-CSS or pure-server-rendered page with no client interactivity
  - Only one isolated effect is needed — use the sibling skill directly (magnetic-button, aurora-gradient, animated-counter, scroll-reveal-section)
  - Heavy WebGL/physics image effects — use image-shatter or interactive-distortion instead
  - Touch-only experiences — tilt and magnetic patterns are pointer:fine hover effects
keywords:
  - framer-level interactions
  - 3d tilt card
  - cursor spotlight
  - magnetic button
  - aurora gradient
  - animated counter
  - sparkline draw-in
  - infinite feed
  - sticky scroll
  - scrollytelling
  - intersectionobserver
  - hover effects
  - micro-interactions
  - hero background
  - stagger reveal
  - prefers-reduced-motion
  - css variables
  - react
  - polish
similar_to:
  - magnetic-button
  - aurora-gradient
  - animated-counter
  - scroll-reveal-section
  - bento-grid
inputs_needed:
  - Which page/sections need the interactions and which of the seven patterns to combine (max two per section)
  - Theme token values or confirmation the CSS vars exist (--rs-accent, --rs-background, --rs-card-color, --rs-text-color, --rs-font, --rs-heading-font)
  - Real data for counters, sparkline points, feed items, and sticky-scroll steps
produces: Plain React components (no heavy deps) implementing the chosen interaction recipes, themed via CSS custom properties and honouring prefers-reduced-motion
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Framer-level interactions

Seven patterns that make a static section page feel alive. Each one is
small, dependency-free, respects `prefers-reduced-motion`, and reads
its theme tokens from CSS custom properties (`--rs-accent`,
`--rs-background`, `--rs-card-color`, `--rs-text-color`, `--rs-font`,
`--rs-heading-font`) so a single pack swap repaints everything.

## When to use

Reach for this skill whenever the user wants a marketing page,
portfolio, product preview, dashboard, or experiential site that
needs to feel like a 2026 Framer template rather than a 2018 Bootstrap
landing. The patterns layer — you'll usually use 3+ on the same page.

## The seven patterns

### 1. 3D tilt + cursor spotlight (feature cards)

```jsx
function TiltCard({ children }) {
  const ref = useRef(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [light, setLight] = useState({ x: 50, y: 50, on: false });

  function move(e) {
    const r = ref.current?.getBoundingClientRect();
    if (!r) return;
    const px = (e.clientX - r.left) / r.width;
    const py = (e.clientY - r.top) / r.height;
    setTilt({ x: (py - 0.5) * 6, y: (px - 0.5) * -6 });   // ±6deg max
    setLight({ x: px * 100, y: py * 100, on: true });
  }
  function leave() { setTilt({ x: 0, y: 0 }); setLight((l) => ({ ...l, on: false })); }

  return (
    <div
      ref={ref}
      onMouseMove={move}
      onMouseLeave={leave}
      style={{
        position: 'relative',
        transition: 'transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1)',
        transformStyle: 'preserve-3d',
        transform: `perspective(1000px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
          opacity: light.on ? 0.6 : 0,
          transition: 'opacity 240ms ease',
          background: `radial-gradient(360px at ${light.x}% ${light.y}%, color-mix(in srgb, var(--rs-accent) 35%, transparent), transparent 60%)`,
        }}
      />
      {children}
    </div>
  );
}
```

**Don'ts:** never tilt beyond ±8°, never apply to non-card elements
(text gets sick-making), never run on touch devices — gate with
`pointer: fine`.

### 2. Magnetic CTA button

```jsx
function MagneticButton({ children, strength = 0.25, ...rest }) {
  const ref = useRef(null);
  const [pos, setPos] = useState({ x: 0, y: 0 });

  function move(e) {
    const r = ref.current?.getBoundingClientRect();
    if (!r) return;
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    setPos({ x: (e.clientX - cx) * strength, y: (e.clientY - cy) * strength });
  }
  function leave() { setPos({ x: 0, y: 0 }); }

  return (
    <button
      ref={ref}
      onMouseMove={move}
      onMouseLeave={leave}
      style={{
        transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
        transition: 'transform 320ms cubic-bezier(0.2, 0.8, 0.2, 1)',
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
```

**Use:** primary CTAs in the hero, "Get tickets" buttons, anything
that earns a hover. Skip on every other button — magnetism loses
meaning when applied everywhere.

### 3. Aurora drift (hero background)

```jsx
function AuroraBg() {
  return (
    <>
      <div aria-hidden="true" style={{
        position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none',
      }}>
        <div style={{
          position: 'absolute', inset: '-20%',
          background: 'radial-gradient(ellipse at 30% 30%, color-mix(in srgb, var(--rs-accent) 35%, transparent), transparent 60%),' +
                      'radial-gradient(ellipse at 70% 70%, color-mix(in srgb, var(--rs-accent) 22%, transparent), transparent 50%)',
          filter: 'blur(60px)',
          animation: 'rs-aurora-drift 22s ease-in-out infinite alternate',
        }} />
      </div>
      <style jsx>{`
        @keyframes rs-aurora-drift {
          0%   { transform: translate3d(-3%, -2%, 0) rotate(0deg); }
          50%  { transform: translate3d( 3%,  2%, 0) rotate(6deg); }
          100% { transform: translate3d(-2%,  3%, 0) rotate(-4deg); }
        }
        @media (prefers-reduced-motion: reduce) {
          div { animation: none !important; }
        }
      `}</style>
    </>
  );
}
```

### 4. Eased number counter (IntersectionObserver + RAF)

```jsx
function Counter({ value, decimals = 0, prefix = '', suffix = '' }) {
  const target = Number(value) || 0;
  const ref = useRef(null);
  const [display, setDisplay] = useState(0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || started) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) { setDisplay(target); setStarted(true); return; }
    const obs = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        setStarted(true); obs.disconnect();
        const dur = 1400, start = performance.now();
        let raf;
        const step = (t) => {
          const p = Math.min(1, (t - start) / dur);
          const eased = 1 - Math.pow(1 - p, 3);            // ease-out-cubic
          setDisplay(target * eased);
          if (p < 1) raf = requestAnimationFrame(step);
          else setDisplay(target);
        };
        raf = requestAnimationFrame(step);
      }
    }, { threshold: 0.4 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, [target, started]);

  const formatted = decimals > 0 ? display.toFixed(decimals) : Math.round(display).toLocaleString();
  return <div ref={ref} style={{ fontVariantNumeric: 'tabular-nums' }}>{prefix}{formatted}{suffix}</div>;
}
```

### 5. Sparkline draw-in (SVG stroke-dashoffset)

```jsx
function Sparkline({ points = [] }) {
  const ref = useRef(null);
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    if (!ref.current || drawn) return;
    const obs = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) { setDrawn(true); obs.disconnect(); }
    }, { threshold: 0.4 });
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, [drawn]);

  const max = Math.max(...points), min = Math.min(...points);
  const range = max - min || 1, width = 100, height = 36;
  const stepX = width / (points.length - 1);
  const path = points.map((v, i) =>
    `${i === 0 ? 'M' : 'L'}${(i * stepX).toFixed(2)},${(height - ((v - min) / range) * height).toFixed(2)}`
  ).join(' ');

  return (
    <svg ref={ref} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true">
      <path
        d={path}
        fill="none"
        stroke="var(--rs-accent)"
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
        style={{
          strokeDasharray: 400,
          strokeDashoffset: drawn ? 0 : 400,
          transition: 'stroke-dashoffset 1400ms cubic-bezier(0.2, 0.8, 0.2, 1)',
        }}
      />
    </svg>
  );
}
```

Add a `<linearGradient>` fill under the stroke if you want the
Framer-style soft area shade.

### 6. Infinite-feed with IO sentinel + stagger reveal

```jsx
const PAGE_SIZE = 9;

function InfiniteFeed({ items = [] }) {
  const [visible, setVisible] = useState(Math.min(PAGE_SIZE, items.length));
  const sentinelRef = useRef(null);

  useEffect(() => {
    if (visible >= items.length) return;
    const obs = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) setVisible((v) => Math.min(items.length, v + PAGE_SIZE));
    }, { rootMargin: '200px 0px' });
    if (sentinelRef.current) obs.observe(sentinelRef.current);
    return () => obs.disconnect();
  }, [visible, items.length]);

  return (
    <>
      <div role="feed" aria-busy={visible < items.length}>
        {items.slice(0, visible).map((it, i) => <FeedCard key={it.id || i} {...it} index={i} />)}
      </div>
      {visible < items.length && <div ref={sentinelRef}>Loading…</div>}
    </>
  );
}
```

Each `FeedCard` runs its own `IntersectionObserver` with a delay
proportional to its `index` (`${Math.min(index, 8) * 60}ms`) so newly
loaded rows cascade in instead of popping.

### 7. Sticky-scroll storytelling (pin + step swap)

```jsx
function StickyStory({ steps = [] }) {
  const [active, setActive] = useState(0);
  const stepRefs = useRef([]);
  useEffect(() => {
    const observers = [];
    stepRefs.current.forEach((el, i) => {
      if (!el) return;
      const obs = new IntersectionObserver((entries) => {
        for (const e of entries) if (e.isIntersecting && e.intersectionRatio > 0.5) setActive(i);
      }, { threshold: [0.5, 0.6, 0.7] });
      obs.observe(el);
      observers.push(obs);
    });
    return () => observers.forEach((o) => o.disconnect());
  }, [steps.length]);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80 }}>
      <div style={{ position: 'sticky', top: '15vh' }}>
        {/* Cross-fade pinned visual */}
        {steps.map((s, i) => (
          <div key={i} style={{
            opacity: i === active ? 1 : 0,
            transform: i === active ? 'scale(1)' : 'scale(0.96) translateY(20px)',
            transition: 'opacity 600ms cubic-bezier(0.2, 0.8, 0.2, 1), transform 600ms cubic-bezier(0.2, 0.8, 0.2, 1)',
            position: i === active ? 'relative' : 'absolute',
          }}>{s.visual}</div>
        ))}
      </div>
      <div>
        {steps.map((s, i) => (
          <div
            key={i}
            ref={(el) => { stepRefs.current[i] = el; }}
            style={{ opacity: i === active ? 1 : 0.35, minHeight: '60vh' }}
          >
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Critical detail: **steps need `min-height: 50-80vh`** or they fly past
before the observer can catch them. Build with three steps first to
tune; add more after.

## Shared rules

- **Always honour `prefers-reduced-motion: reduce`.** Either disable
  the animation, snap to the final state, or use a 0-duration variant.
- **Use easing, not linear.** Default to
  `cubic-bezier(0.2, 0.8, 0.2, 1)` (sometimes called "ease-out-back").
- **Read theme tokens from CSS vars**, not hard-coded hex. The whole
  system swaps with a theme pack change.
- **Use `transform` + `opacity`** for any animation. Never animate
  `width`, `height`, `top`, `left`, `padding` — they re-layout.
- **`will-change` is a trap.** Skip it unless you've measured a
  paint problem. Browsers do the right thing automatically.

## Composition rule

These patterns work in stacks, not standalone. A typical "Framer-grade"
hero is: AuroraBg + MagneticButton + ScrollReveal'd subhead. A
product-feature section is: TiltCard × 4-6 in a bento grid + a Counter
strip below. Don't pick one and call it done.

## Anti-patterns

1. **All seven patterns on one section** — visual chaos. Pick two
   max per section.
2. **Tilting headings** — only cards, never type.
3. **Magnetic everywhere** — special button only.
4. **Counter without IntersectionObserver** — it animates on page load
   before the user has seen it, defeating the reveal.
5. **Sticky-scroll with one step** — just use a static section.
6. **Infinite feed without a "you're caught up" terminator** — feels
   broken when the items end.
