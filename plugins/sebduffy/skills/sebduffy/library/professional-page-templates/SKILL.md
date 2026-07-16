---
name: professional-page-templates
category: frontend-and-design
description: >
  Build professionally-designed marketing pages, product sites,
  portfolios, dashboards, conference pages, newsrooms, and experiential
  scrollytelling sites — across genuinely different layout shapes, not
  just colour-swapped landing pages. Covers a section taxonomy of 20+
  block types organised into categories (Hero, Social Proof, Features,
  Visual, Metrics, Narrative, Content, Interactive, Product, Pricing,
  FAQ, CTA, Footer) and 11 starter compositions (SaaS landing, agency
  portfolio, product launch, startup metrics, indie creator, creator
  portfolio, community event, newsroom, dashboard-product, portfolio
  feed, experiential art). Every section reads CSS-variable theme
  tokens so a pack swap repaints the whole page. Trigger when the user
  asks for a "professional-looking website", says the current
  templates "all feel the same" or "are basically tabs", asks for a
  "dashboard / portfolio / experiential / portfolio / infinite-scroll"
  page shape, or wants "Lovable-level" template variety. Trigger even
  if they only name one shape — they typically want the system, not
  one starter. SKIP only if the user explicitly wants a single
  hand-coded one-off page with no reuse intent.
when_to_use:
  - User asks for a "professional-looking website" or a marketing site, product page, portfolio, dashboard, conference page, newsroom, or experiential/scrollytelling page
  - User says the current templates "all feel the same" or "are basically tabs" and wants Lovable-level template variety
  - User names one page shape (dashboard / portfolio / experiential / infinite-scroll) — they typically want the whole starter system, not one page
  - Composing a 5-9 section page from the section taxonomy with no two adjacent sections from the same category
  - Adding a new section type to the registry (component + sectionRegistry + editableSchemas + defaults) or a new 30-line starter
  - Swapping or building theme packs so a single pack change repaints every section via CSS variables
when_not_to_use:
  - User explicitly wants a single hand-coded one-off page with no reuse intent — use frontend-design instead
  - The work is only motion/interaction polish on existing sections — that is the framer-level-interactions layer
  - You only need a new colour/typography pack, not page structure — use theme-factory
  - Fixed-brand typography and colour decisions alone — see brand-guidelines
keywords: [page templates, marketing site, landing page, section taxonomy, starter shapes, saas landing, agency portfolio, product launch, newsroom, dashboard product, portfolio feed, experiential art, scrollytelling, theme pack, css variables, theme tokens, hero, pricing, faq, section registry]
similar_to: [frontend-design, theme-factory, bento-grid, scroll-reveal-section]
inputs_needed:
  - What kind of page/site the user wants (SaaS landing, agency, launch, metrics, creator, event, newsroom, dashboard, feed, experiential) to pick a starter
  - Brand vibe or preferred theme pack (dark-tech, editorial-mono, pastel-soft, corporate-blue, vibrant-pop, premium-dark, neon-club) or tokens for a custom pack
  - Whether an existing starter fits or a new starter/section type must be built
produces: A composed 5-9 section page (starter sequence + registered sections + theme pack) rendered from the section registry with CSS-variable theming
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Professional page templates

A section taxonomy + starter shape system that delivers genuinely
different page layouts — not the same hero-then-features-then-CTA
template with different colours.

The system separates **what** (section types — the registry) from
**how it's composed** (starters — sequences of sections) from **how
it looks** (theme packs — CSS variable bundles). Swapping any one of
the three changes the page without breaking the others.

## When to use

Reach for this skill whenever you're being asked to design or generate
a marketing site, product page, portfolio, dashboard, conference page,
newsroom, or experiential page. It pairs naturally with
[[framer-level-interactions]] (the motion layer) and
[[autosuggestive-schema-builder]] (the AI-driven editor).

## Section taxonomy

20+ section types organised by category. Each is one React component
in `components/page-sections/`; each reads CSS-variable theme tokens;
each accepts a strongly-typed props blob. Most rendered top-to-bottom
on a single vertical-scroll page.

| Category | Sections |
|---|---|
| **Hero** | `hero-aurora` (gradient + magnetic CTA), `video-hero` (full-bleed loop) |
| **Social Proof** | `marquee-row` (infinite logos/pills), `testimonial-quote` (block quote) |
| **Features** | `feature-bento` (3D-tilt cards), `split-feature` (text + visual, flippable) |
| **Visual** | `image-gallery` (responsive grid) |
| **Metrics** | `stats-counters` (eased numbers), `comparison-table` (us-vs-them) |
| **Narrative** | `timeline-vertical`, `sticky-scroll-story` (Stripe-style pin + steps) |
| **Content** | `blog-grid`, `infinite-feed` (IO-sentinel lazy load) |
| **Interactive** | `tabs-section` (ARIA tablist + chip nav) |
| **Product** | `dashboard-preview` (chrome + sidebar + sparkline + activity), `kanban-board` |
| **Pricing** | `pricing-columns` (3-up with featured tier) |
| **FAQ** | `faq-accordion` |
| **CTA** | `cta-band`, `newsletter-signup` |
| **Footer** | `footer-block` (link columns + legal) |

## Composition discipline

A page is a 5-9 section sequence. **Variety is the rule.** No two
adjacent sections from the same category. A page is wrong if it reads:

> Hero · Features · Features · Features · CTA · Features

It's right if it reads:

> Hero · Social Proof · Features · Metrics · Narrative · Pricing · FAQ · CTA · Footer

Each section earns its place by serving a different job to the
visitor.

## Starter shapes (eleven distinct sequences)

Starters live in `lib/config/pages/starters.js`. Each is a tuple of
`{ id, kicker, description, pack, accent, sections[] }`. The
shape — not the copy — is what makes them different.

1. **SaaS landing** (`saas-landing`, `midnight-tech`) — Hero · Marquee
   · FeatureBento · SplitFeature · PricingColumns · FAQAccordion ·
   CTABand
2. **Agency portfolio** (`agency-portfolio`, `editorial-mono`) — Hero
   · Marquee · SplitFeature × 2 · FeatureBento · CTABand
3. **Product launch** (`product-launch`, `vibrant-pop`) — Hero · Bento
   · Marquee (pills) · Pricing · FAQ · CTA
4. **Startup metrics** (`startup-metrics`, `corporate-blue`) — Hero ·
   StatsCounters · TestimonialQuote · Bento · FAQ · CTA · Footer
5. **Indie creator** (`indie-creator`, `pastel-soft`) — Hero ·
   SplitFeature · Bento · Marquee · CTA
6. **Creator portfolio** (`creator-portfolio`, `premium-dark`) —
   VideoHero · ImageGallery · TimelineVertical · CTA · Footer
7. **Community event** (`community-event`, `neon-club`) — Hero ·
   Marquee · TimelineVertical · PricingColumns · FAQ · Newsletter ·
   Footer
8. **Newsroom** (`newsroom`, `editorial-warm`) — Hero ·
   ComparisonTable · BlogGrid · Marquee · Newsletter · Footer
9. **Dashboard product** (`dashboard-product`, `midnight-tech`) — Hero
   · DashboardPreview · TabsSection · KanbanBoard · Pricing · CTA ·
   Footer
10. **Portfolio feed** (`portfolio-feed`, `editorial-mono`) — Hero ·
    InfiniteFeed · TimelineVertical · CTA · Footer
11. **Experiential art** (`experiential-art`, `premium-dark`) —
    VideoHero · StickyScrollStory · ImageGallery · TestimonialQuote ·
    Newsletter · Footer

Each pairs naturally with one theme pack but the binding is loose —
the user can swap packs and the page still works.

## Theme pack cascade

The pack is a flat bag of theme tokens that the renderer compiles
into CSS variables on a root `<main>` element. Every section reads
those variables, so changing one pack repaints the entire page.

Required tokens per pack:

```js
{
  id: 'midnight-tech',
  displayName: 'Midnight Tech',
  theme: {
    accentColor:    '#4DDCFF',
    backgroundColor: '#0A0A0F',
    cardColor:       '#15151C',
    textColor:       '#FFFFFF',
    fontFamily:      'Inter Tight',
    headingFontFamily: 'Inter Tight',
  },
}
```

Compiled at render-time into:

```css
--rs-accent: #4DDCFF;
--rs-background: #0A0A0F;
--rs-card-color: #15151C;
--rs-text-color: #FFFFFF;
--rs-font: 'Inter Tight', system-ui, sans-serif;
--rs-heading-font: 'Inter Tight', system-ui, sans-serif;
```

A solid pack library covers: a dark-tech pack, an editorial-mono pack
(black/white serif-adjacent), an editorial-warm pack, a pastel-soft,
a corporate-blue, a vibrant-pop, a premium-dark (gold accent), a
neon-club (cyberpunk magenta). Eight packs span ~90% of brand vibes;
add custom packs from saved client work.

## Picking the right starter

| If the user says… | Reach for |
|---|---|
| "SaaS landing" | `saas-landing` or `dashboard-product` |
| "Agency / studio" | `agency-portfolio` |
| "We're launching a hardware product" | `product-launch` |
| "We just raised / show off metrics" | `startup-metrics` |
| "Personal site / I'm a designer/writer" | `indie-creator` |
| "Photographer / film" | `creator-portfolio` or `experiential-art` |
| "Conference / event" | `community-event` |
| "Editorial / magazine / blog" | `newsroom` |
| "Show me how the product feels" | `dashboard-product` |
| "Portfolio with lots of work" | `portfolio-feed` |
| "Scrollytelling / story-driven" | `experiential-art` |

If a starter doesn't fit, build a new one — don't compromise. A new
starter is 30 lines of declarative JSON.

## How to add a new section type

1. Build the component in `components/page-sections/<Name>.jsx` — read
   theme tokens from `var(--rs-*)`, accept all props as named args,
   default arrays to `[]`.
2. Register in `lib/config/pages/sectionRegistry.js`:
   `'kebab-id': { component: Name, displayName: 'Display Name', category: 'Category' }`.
3. Declare editable props in `lib/config/pages/editableSchemas.js`:
   `EDITABLE_PROPS['kebab-id'] = [{ key, label, type, options? }]`
   and any object arrays in `EDITABLE_ARRAYS['kebab-id']`.
4. Add a `defaultsFor('kebab-id')` case so new sections start with
   sensible content, not empty fields.
5. (Optional) Add a starter that uses it.

Anything beyond that — like wiring up the builder UI or the AI prompt
— happens automatically because both read from the registry +
schemas.

## Anti-patterns

1. **One mega "landing" template with optional blocks.** Real
   variety needs distinct section *sequences*, not a configurator.
2. **Heroes that always look the same.** Mix `hero-aurora`,
   `video-hero`, and the occasional `short` height with a
   `marquee-row` immediately below. Don't default to
   `hero-aurora · marquee-row` for everything.
3. **Footers only on landing pages.** Every published page should
   have a footer — it's where the brand mark + legal live.
4. **Hard-coded colours inside section components.** Always
   `var(--rs-accent)` so theme swap repaints.
5. **Sections without a `data-section` attribute.** Adding
   `data-section="<id>"` to the section root lets the LivePreview,
   E2E tests, and Cypress scrapes target sections precisely.

## Compatibility

Pairs with:
- [[framer-level-interactions]] — the seven motion patterns each
  section uses.
- [[autosuggestive-schema-builder]] — the AI-driven editor that
  manipulates this taxonomy.
- [[theme-factory]] — for building new theme packs.
- [[brand-guidelines]] / [[vccp-media-design]] — for the typography
  + colour bedrock when the brand is fixed.
