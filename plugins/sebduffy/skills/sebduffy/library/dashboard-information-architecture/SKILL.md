---
name: dashboard-information-architecture
category: frontend-and-design
description: >-
  Lay out data-dense dashboards so they actually get READ — decide KPI
  hierarchy, scan order, density-tier grids, and drill-down layering BEFORE any
  chart is styled. Reach for this when a dashboard feels like a wall of equal
  tiles, when everything competes for attention, when stakeholders ask "so
  what's the headline?", or when you must fit twenty metrics on one screen
  without it becoming soup. Gives a five-question framing pass, an inverted-
  pyramid layout formula, a concrete 12-column CSS grid with three density
  tiers, an overview→focus→detail drill model, and a scan-order audit. This is
  information design (what goes where, how big, in what order) — NOT chart
  colouring or axis styling.
when_to_use:
  - A dashboard reads as a flat wall of same-size cards with no clear headline metric
  - You must place many KPIs and charts on one screen and need a density + priority plan
  - Stakeholders can't tell in 5 seconds what the single most important number is
  - You are deciding what belongs on the overview vs behind a drill-down or filter
  - Reviewing an existing dashboard's scan order / visual hierarchy before a redesign
  - Splitting one bloated dashboard into role-based views (exec vs analyst vs ops)
when_not_to_use:
  - You are choosing chart types, colours, axes, tooltips or legends — use the dataviz skill
  - You need a full dashboard scaffolded and running fast, not an IA plan — use quick-dashboard
  - You want fluid type/space tokens for the grid — use fluid-responsive-system
  - The screen is a single chart or one KPI, not a composed multi-metric surface — dataviz is enough
  - You need colour tokens or contrast for the tiles — use brand-color-token-system / accessible-contrast-checker
keywords:
  - dashboard
  - information architecture
  - kpi hierarchy
  - visual hierarchy
  - scan order
  - drill down
  - data density
  - inverted pyramid
  - f-pattern
  - z-pattern
  - grid layout
  - overview detail
  - progressive disclosure
  - card layout
  - analytics ux
similar_to:
  - fluid-responsive-system
  - dataviz
  - print-editorial-layout
  - quick-dashboard
  - motion-system
inputs_needed: >-
  The list of metrics/charts to show, who the primary viewer is (exec / analyst
  / operator) and the ONE decision they make from it, plus the target surface
  (single screen, scroll page, or TV wall). Optional: an existing dashboard
  screenshot or markup to audit.
produces: >-
  A prioritised metric map (primary / secondary / supporting tiers), an
  inverted-pyramid layout plan, a runnable 12-column CSS grid with three density
  tiers and span classes, a drill-down layering model, and a scan-order audit
  checklist.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Dashboard Information Architecture

Decide **what goes where, how big, and in what order** before a single chart is
styled. Most bad dashboards fail at IA, not at charting: every tile is the same
size, so nothing is the headline, and the eye has nowhere to land. This skill
fixes the layout of *meaning*. For the charts themselves, hand off to `dataviz`.

## When to use

Use this the moment a dashboard has more than ~4 tiles, serves a specific viewer
who makes a specific decision, or already exists and reads as undifferentiated
soup. Do the framing pass first; it changes the grid.

## Prerequisites

Have the raw ingredients written down: the metric list, the primary viewer, and
the one question they open the dashboard to answer. If you can't name that
question, stop and get it — an IA with no lead question can only produce a wall.

## Step 1 — Five-question framing pass

Answer these before touching layout. They set the hierarchy.

1. **Who is the primary viewer?** Exec, analyst, or operator. One primary — if
   you have three audiences you have three dashboards (or one with role views).
2. **What ONE decision do they make from this?** e.g. "should I intervene this
   week?" The headline metric is whatever most changes that decision.
3. **What is the single hero metric?** Exactly one. It gets the biggest tile,
   top-left of the content well, largest type. Everything else is smaller.
4. **What is the comparison?** A number alone is noise. Every KPI needs a
   reference: vs target, vs prior period, vs benchmark. Decide it now.
5. **What is diagnostic vs supporting?** Diagnostic = explains *why* the hero
   moved (drivers, breakdowns). Supporting = context you glance at rarely.

Output a three-tier **metric map**:

- **Primary (1):** the hero KPI + its comparison.
- **Secondary (2–5):** diagnostics that explain the hero.
- **Supporting (rest):** context, long tail, drill-only.

## Step 2 — Inverted-pyramid layout

Lay the page out like a news story: conclusion first, evidence below, detail
last. Reading order in LTR locales follows an **F / Z pattern** — the top-left
is seen first and longest, so the hero lives there.

```
┌──────────────────────────────┬───────────────┐
│  HERO KPI (big number +       │  2–3 secondary│   ← top band: the "so what"
│  trend vs target)             │  KPI tiles    │
├──────────────────────────────┴───────────────┤
│  Primary diagnostic chart (trend over time)   │   ← middle: the "why"
├───────────────┬───────────────┬───────────────┤
│  breakdown A  │  breakdown B  │  breakdown C  │   ← drivers row
├───────────────┴───────────────┴───────────────┤
│  Detailed table / supporting long tail        │   ← bottom: the "detail"
└───────────────────────────────────────────────┘
```

Rules that make the pyramid work:

- **Size encodes priority.** The hero tile is visibly the largest. If two tiles
  are equal size, you are claiming equal importance — usually a lie.
- **One hero per view.** Multiple "biggest" tiles cancel out; the eye bounces.
- **Group by question, not by chart type.** All tiles answering "why did revenue
  drop?" sit together, regardless of whether they're bars, lines, or numbers.
- **Left-to-right = general-to-specific; top-to-bottom = summary-to-detail.**

## Step 3 — The 12-column density grid

Use a 12-column grid so tiles snap to a shared rhythm. Pick **one density tier**
per dashboard based on viewer distance and metric count.

| Tier | Viewer / use | Gap | Min tile | Metrics/screen |
|------|--------------|-----|----------|----------------|
| Comfortable | exec, glanceable, projector | 24px | ~280px | ≤ 8 |
| Compact | analyst working surface | 16px | ~220px | 8–16 |
| Dense | ops / trading / NOC wall | 8px | ~160px | 16+ |

```css
:root { --gap: 16px; }               /* swap per density tier */

.dash {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--gap);
  align-items: start;
}

/* span helpers — compose the pyramid */
.col-3  { grid-column: span 3;  }
.col-4  { grid-column: span 4;  }
.col-6  { grid-column: span 6;  }
.col-8  { grid-column: span 8;  }
.col-12 { grid-column: span 12; }
.row-2  { grid-row: span 2; }        /* let the hero be taller too */

/* collapse gracefully: below ~720px every tile goes full width */
@media (max-width: 720px) {
  .dash { grid-template-columns: 1fr; }
  .dash > * { grid-column: 1 / -1 !important; }
}
```

Pyramid in markup — hero is `col-8 row-2`, secondaries are `col-4`:

```html
<div class="dash">
  <section class="tile col-8 row-2"><!-- HERO KPI + trend --></section>
  <section class="tile col-4"><!-- secondary KPI --></section>
  <section class="tile col-4"><!-- secondary KPI --></section>
  <section class="tile col-12"><!-- primary diagnostic chart --></section>
  <section class="tile col-4"><!-- breakdown A --></section>
  <section class="tile col-4"><!-- breakdown B --></section>
  <section class="tile col-4"><!-- breakdown C --></section>
  <section class="tile col-12"><!-- detail table --></section>
</div>
```

Density craft: increase density by **tightening gaps and shrinking chrome**
(padding, borders, tile titles), NOT by shrinking the data ink. Kill tile
borders in favour of whitespace separation; borders add visual noise that reads
as clutter at high density. Right-align numbers, use tabular figures
(`font-variant-numeric: tabular-nums`) so columns line up and scan vertically.

## Step 4 — Drill-down layering (progressive disclosure)

A dashboard is three depth layers, not one flat surface. Push detail down so the
overview stays scannable.

- **Overview (default):** the pyramid above. Answers "is anything wrong?" in ~5s.
- **Focus (in-place):** hover tooltips, a segmented control to switch dimension,
  a period toggle. Same tiles, more precision — no navigation.
- **Detail (on demand):** click a tile → row expands, a drawer/panel opens, or
  you route to a sub-view with the full table and raw records.

Layering rules:

- **Overview shows shape; detail shows values.** Don't put a 500-row table on the
  overview — put its headline (top 3, or a total) and drill to the rest.
- **Detail inherits context.** Clicking a bar filters the detail to that bar; the
  user should never re-specify what they just clicked.
- **Filters are focus, not detail.** A global filter bar (date range, segment)
  belongs at the top of the overview and re-scopes every tile at once.
- Keep drill transitions cheap and reversible; see `motion-system` for the
  expand/collapse motion so it reads as depth, not a page swap.

## Step 5 — Scan-order audit

Run this on any dashboard (yours or an inherited one). Squint test first: blur
your eyes — the thing that stays visible should be the hero. If nothing
dominates, the hierarchy is flat.

- [ ] In 5 seconds, can a first-timer name the ONE headline metric?
- [ ] Is exactly one tile visibly the largest / top-left?
- [ ] Does every KPI carry a comparison (vs target / prior / benchmark)?
- [ ] Are tiles grouped by the question they answer, not by chart type?
- [ ] Does reading top→bottom go summary→detail (inverted pyramid intact)?
- [ ] Is there one consistent density tier (gaps + tile sizes coherent)?
- [ ] Are numbers right-aligned with tabular figures for vertical scanning?
- [ ] Is detail pushed to hover/click, keeping the overview uncluttered?
- [ ] Does it collapse to a sensible single-column order on narrow screens?
- [ ] Would removing any tile lose a decision? If not, cut it (KISS/YAGNI).

## Verify

Load the grid in a browser and apply the squint test. Then check the DOM reading
order matches the visual pyramid — screen-reader and keyboard users get source
order, so the hero tile should come *first* in markup, not just be positioned
first. Tab through: focus order should walk primary → secondary → detail. Resize
to 700px: every tile should stack full-width in priority order without
horizontal scroll.

## Pitfalls

- **Everything-is-a-KPI wall.** Equal tiles = no hierarchy. Pick one hero; demote
  the rest. This is the single most common failure.
- **Numbers without comparison.** "£1.2M" tells no one if that's good. Always
  pair with vs-target or vs-prior; the delta is the message.
- **Density by shrinking data ink.** Squeezing charts to fit more is worse than
  drilling. Cut chrome and use layers instead.
- **Grouping by chart type.** A row of "all the bar charts" scatters related
  answers. Group by the question.
- **Visual order ≠ DOM order.** CSS grid lets you place the hero top-left while it
  sits last in markup — an accessibility trap. Keep source order = priority order.
- **Serving three audiences on one screen.** Split into role views; a shared
  overview + drill-outs beats a compromise nobody can scan.
- **Styling charts here.** Colour, axis, legend, tooltip decisions belong to
  `dataviz` — do IA first, then style within the tiers you set.
