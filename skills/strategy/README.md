# Strategy

**Advertising, media, research and analytic strategy — the
planner's toolkit.**

These skills are written for the hybrid strategist / planner /
analyst / researcher role: someone who interrogates a brief,
parses the raw data, runs the stats, excavates the insight,
writes the strategy, plans the channel response, and shapes the
deck. Each skill is self-contained, points to the next, and
hands off cleanly to the design system in
[`vccp-media-design`](../frontend-and-design/vccp-media-design).

## Index

### Research & data — *building the evidence*

| Skill | Use for |
|---|---|
| [`raw-data-research`](raw-data-research) | Write and execute scripts to parse, clean and normalise raw data (PDFs, scrapes, multi-sheet XLSX, JSON dumps, transcripts). Pipeline before analysis. |
| [`data-analyst`](data-analyst) | Proper EDA, hypothesis tests, regression, time-series decomposition, A/B / lift / incrementality. The analytic substrate. |
| [`data-cut-headline-stats`](data-cut-headline-stats) | Cut a dataset and pull out the 3–7 stats worth a client slide, comparator-led and caveated. |
| [`qualitative-research`](qualitative-research) | Run the qual lifecycle — discussion guides, IDIs / groups / ethno, theme coding, synthesis. |
| [`developed-research`](developed-research) | Long-form immersive briefs, category reviews, sector POVs, audience deep dives, brand archaeology. |

### Audience & insight — *understanding the people*

| Skill | Use for |
|---|---|
| [`audience-insight`](audience-insight) | Excavate the human insight with tension. Recognition / tension / brand-fit tests. |
| [`audience-segmentation`](audience-segmentation) | Build, name, profile and deploy segmentations — or interpret one a client owns. |
| [`cultural-semiotics`](cultural-semiotics) | Decode category codes (Residual / Dominant / Emergent), spot cultural tensions, recommend code-shifts. |
| [`trend-foresight`](trend-foresight) | Spot signals, separate fads from trends, time-horizon and weight them, write a foresight POV. |

### Strategy — *what to do about it*

| Skill | Use for |
|---|---|
| [`advertising-strategy`](advertising-strategy) | Build a comms / advertising strategy from a brief: problem → audience → insight → role → SMP → RTB → measures. |
| [`advertising-strategy-copy`](advertising-strategy-copy) | The *prose* — propositions, manifestos, audience portraits, tone of voice, ban-list-enforced. |
| [`media-strategy`](media-strategy) | Channel role, brand/activation split, attention-adjusted reach, ESOV, share of search, flighting, test-and-learn. |

### Audit & competitive — *reading the field*

| Skill | Use for |
|---|---|
| [`brand-audit`](brand-audit) | Audit a brand's distinctive assets, mental availability, share metrics, coherence, behaviour, drift. |
| [`competitive-comms-audit`](competitive-comms-audit) | Map competitors across positioning, codes, share, platform stability, white-space. |
| [`share-of-search`](share-of-search) | Compute and interpret share of search (Binet/Hankins) as a leading indicator. |

### Read-out & effectiveness — *making the case*

| Skill | Use for |
|---|---|
| [`strategy-analyst`](strategy-analyst) | The hybrid analyst-strategist read: hypothesis → triangulate → fact / inference / recommendation. |
| [`deck-flow-structure`](deck-flow-structure) | Plan the order of a deck before any slide is built — SCQA / story spine / pyramid. |
| [`effectiveness-case`](effectiveness-case) | Write an IPA-standard effectiveness case with counterfactuals, triangulation, payback. |

## How they fit together

```
                  raw-data-research ──┐
                                       ├──► data-analyst ──► data-cut-headline-stats
qualitative-research ──► audience-insight ──┐                       │
                                              ├──► advertising-strategy ──► advertising-strategy-copy
developed-research ──► cultural-semiotics ────┤                            │
                                              │                            ├──► deck-flow-structure ──► vccp-media-design
audience-segmentation ────────────────────────┤                            │
                                              ├──► media-strategy ────────┤
trend-foresight ──────────────────────────────┤                            │
                                              │                            │
brand-audit ──► competitive-comms-audit ──► share-of-search ──► strategy-analyst
                                                                            │
                                                                            └──► effectiveness-case
```

## Typical sequences

- **New client brief →** `advertising-strategy` (rebrief) +
  `data-cut-headline-stats` (context) + `advertising-strategy-copy`
  (write-up) + `deck-flow-structure` (spine) + `vccp-media-design` (visual)

- **Tracker / MMM / campaign data dropped →**
  `raw-data-research` → `data-analyst` → `strategy-analyst` →
  `advertising-strategy-copy` → `deck-flow-structure`

- **Pitch immersion (two weeks) →**
  `developed-research` + `cultural-semiotics` +
  `competitive-comms-audit` + `brand-audit` + `share-of-search`
  → `audience-insight` → `advertising-strategy` →
  `media-strategy` → `deck-flow-structure`

- **Year-end review →** `brand-audit` + `share-of-search` +
  `data-analyst` → `strategy-analyst` → `effectiveness-case`

- **Qual study → strategy →** `qualitative-research` →
  `audience-insight` → `audience-segmentation` →
  `advertising-strategy`

- **Foresight / "trends 2027" piece →** `trend-foresight` +
  `cultural-semiotics` + `developed-research` →
  `advertising-strategy-copy` (write-up)

## Related skills outside this category

- **[`vccp-media-design`](../frontend-and-design/vccp-media-design/)** — the VCCP brand system that styles the output of every strategy skill (web, PPTX, PDF, posters, charts, social tiles)
- **[`pptx`](../documents/pptx/)** — render the deck to PowerPoint
- **[`xlsx`](../documents/xlsx/)** — read / write spreadsheet inputs
- **[`pdf`](../documents/pdf/)** — render strategy docs to PDF
- **[`market-research`](../product/market-research/)** — broader market / competitor research before strategy
- **[`deep-research`](../product/deep-research/)** — multi-source research before a pitch
- **[`internal-comms`](../documents/internal-comms/)** — translate strategy outputs into internal updates and FAQs

## Conventions inside this category

- **Sentence case in all written outputs.** No Title Case.
- **No agency clichés.** Banned-word list lives in `advertising-strategy-copy`.
- **Confidence registers.** *We know / we think / we're watching* — used across every data-led output.
- **Comparators inside the sentence.** A stat without a benchmark isn't a headline.
- **One claim per slide.** A slide answering two questions is two slides.
- **Hand-off discipline.** Each skill names the next one in the chain.
- **Counterfactual hygiene.** Every effectiveness claim names what it's measured against.
- **Sources cited, evaluated, ranked.** Especially in `developed-research` and `effectiveness-case`.
