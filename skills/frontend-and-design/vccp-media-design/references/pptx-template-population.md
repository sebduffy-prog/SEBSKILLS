# PPTX: build INSIDE the real template gallery (do not hand-draw on a blank canvas)

The right way to produce a VCCP Media (or VCCP corporate) deck is to
**clone a real designed slide from the matching template and
repopulate its placeholder text**, not to draw text boxes and
rectangles on a blank `Presentation()`. Hand-drawing loses the master
backgrounds, rails, highlighter furniture, page numbers and, most
dangerously, puts you in control of text colour, which is how you end
up with dark-on-dark. When you repopulate a real template slide, the
text keeps the template's own colour for that background, so a dark
closing slide keeps its light text for free.

**Only ever use the native `.pptx` files.** The method below is an
OOXML operation (`python-pptx` deep-copying real slide XML). It does
not work on `.odp` (a different XML schema `python-pptx` cannot open
at all) or on a PDF (flattened, non-editable). If a template only
exists as a PDF, get the original editable file from whoever designed
it rather than trying to populate the PDF directly.

## The template gallery

All files live at `~/Desktop/VCCP Templates/`, `.pptx` only:

| File | Use it for | Slides | Canvas |
|---|---|---|---|
| `VCCP MEDIA/Pitch Template 2026 [Q2].pptx` | General new-business pitch decks — the widest archetype gallery; default when nothing more specific fits | 133 | 16:9, 10800000×6076800 EMU |
| `VCCP MEDIA/Strategy & Planning Template 2026 [Q2].pptx` | Strategy / planning decks | 129 | 16:9, same EMU |
| `VCCP MEDIA/VCCP Media Creds 2026 [Q1] .pptx` | Capabilities / credentials decks | 63 | 16:9, same EMU |
| `VCCP MEDIA/Portrait Template A4 2026 [Q2].pptx` | A4 portrait one-pagers / documents | 28 | A4 portrait, 7560000×10692000 EMU |
| `VCCP MEDIA/VCCPx Ideas Book TEMPLATE 118x210 2026 [Q2].pptx` | Small printed "ideas book" pages | 3 | 118×210mm, 7776000×4464000 EMU |
| `VCCP MEDIA/TRUMP CARD MASTER A5 2026 [Q2].pptx` | Staff/team bio "trump cards" | 13 | A5, 7776000×5544000 EMU |
| `VCCP MEDIA/SOAP & POAP A4 2026 [Q2].pptx` | Single-page strategy/creative-platform frameworks | 2 | A4 portrait |
| `VCCP MEDIA/VCCP Media CIM Card 2026 [Q2].pptx` | Single category-insight-map card | 1 | 16:9 |
| `VCCP/_VCCP Brand Guidelines_Dec 2025.pptx` | Not a build template — the corporate brand *rulebook* (Frame, Patterns, colour, typography, the highlighter rule). Read, don't clone from, unless the ask is literally "the brand guidelines deck". | 32 | 10"×5.62" |

There is no longer a single "Media Template 2026 [Q2].pptx" file —
`Pitch Template 2026 [Q2].pptx` is its modern replacement and carries
the same cover/quote/agenda/divider/closing archetype family (see
below); `Strategy & Planning Template 2026 [Q2].pptx` and
`VCCP Media Creds 2026 [Q1].pptx` carry the same family at different
slide indices.

**Layout names are not archetype labels.** These decks were built in
Google Slides then exported (shape names like
`Google Shape;1026;p101` give it away), and each slide got its own
auto-generated layout — `slide.slide_layout.name` returns things like
`TITLE_AND_BODY_1_4_2_5_1_3`, effectively unique per slide, not a
small reusable set. **Find archetypes by placeholder marker text
instead**, as below.

### Archetype marker index (verified indices, 2026-07-24 audit)

| Archetype | `Pitch Template 2026 [Q2]` | `Strategy & Planning 2026 [Q2]` | `VCCP Media Creds 2026 [Q1]` | Placeholder markers to replace |
|---|---|---|---|---|
| Cover (client-branded) | 2 | — | — | `01･04･26` (date), `VCCP Media x Company`, `Company logo here` |
| Cover (plain) | 4 | — | — | `Media Template 2026`, `01･04･26` |
| Headline only (chart under it) | 61 | 63 | 47 | `Example headline goes here` |
| Headline + body + source | 62 | 64 | 48 | `Example headline goes here`, `Body copy here`, `Source copy here` |
| Agenda (numbered chapters) | 70 | 7 | 10 | `Today's agenda`, `01`/`02`/`03` + chapter labels |
| Divider (chapter breakdown) | 78, 88 | 7 | — | `Chapter heading` (×N), `Agenda` |
| Divider (simple) | 89 | 8 | 43 | `Divider heading`, `01` |
| Quote | 115 | — | — | `Name Surname`, `Example of inspirational quotation goes in here` |
| Closing (dark bg) | 114 | 105 | 14 | `We are VCCP. We do Media. We just do it differently.` |

`—` means not independently verified at time of writing; search for
the marker text yourself with the snippet below before assuming it's
absent — these decks are large and only a sample of slides were
checked archetype-by-archetype.

```python
from pptx import Presentation
prs = Presentation(PATH)
marker = "Example headline"
for i, slide in enumerate(prs.slides):
    text = " ".join(sh.text_frame.text for sh in slide.shapes if sh.has_text_frame)
    if marker.lower() in text.lower():
        print(i, text[:120])
```

Backgrounds: cover/quote sit on a light accent (Mustard or
Eggshell/`lt2`); the workhorse content slides are white (`#FFFFFF`)
so **white-background charts blend perfectly**; the closing slide is
dark (Mustard `dk2` in these files, not literally black — check the
specific slide) with native light text. Put charts only on the white
slides, never on cover/closing/accent slides.

## The highlighter parallelogram — clone it, never redraw it

The template's "highlighter" motif (a solid-colour parallelogram
behind one accent word — see the brand guidelines deck, slides 16–17,
and the full rule in the main `SKILL.md`) is present **358 times**
across this gallery. The one thing that has actually gone wrong in
practice: someone inserts a *fresh* `MSO_SHAPE.PARALLELOGRAM` from the
shapes menu and guesses at the skew, instead of duplicating one that's
already in the template. Audited across the whole gallery, 340 of 358
(95%) use `adjustments[0] = 0.25` — which is also PowerPoint's own
stock default for this shape. If you must build one from scratch
(rather than duplicating), use `0.25`, not any other value. Every
real instance also has zero outline (`line.fill.type == BACKGROUND`,
`line.width == 0`) and sits at or near the back of its slide's shape
order (added first) so the text sits on top of it, never the other
way round. A highlighter never covers more than one word or a short
phrase — never a full line, never spanning a line break.

## Method (cloning an archetype slide)

1. `prs = Presentation(TEMPLATE)` — open the real template file for
   the job (see gallery table above).
2. For each slide you need, `duplicate(archetype_index)` (helper
   below) to clone a designed slide, then repopulate its placeholders
   by marker text.
3. Add chart PNGs as pictures on the white content slides; add a
   small source line as a new Inter-Tight-muted textbox if the
   archetype has no source field.
4. When all your slides are built (they append at the end), **delete
   the original template slides** by removing the first N
   `<p:sldId>` from `prs.slides._sldIdLst`.
5. Save. Then **optimise for Drive**: strip unused `slideLayouts` and
   any media no remaining part references (zip surgery). Note the
   bulk of template media lives in the slide *master*
   (brand backgrounds/logos) and cannot be removed without losing the
   look, so a template-native deck floors at roughly the source
   template's own size. That is within Drive/Google-Slides limits.
   Only go leaner (a fresh `Presentation()`, well under 1 MB) if the
   user explicitly wants size over template-nativeness.

## Working code

```python
import copy
from pptx.oxml.ns import qn

def duplicate(prs, index):
    """Clone a slide (design + images) into a new slide at the end."""
    src = prs.slides[index]
    new = prs.slides.add_slide(src.slide_layout)
    for sh in list(new.shapes):                       # strip layout placeholders
        sh._element.getparent().remove(sh._element)
    id_map = {}                                        # remap image rels
    for rId, rel in src.part.rels.items():
        if rel.reltype.endswith("/image") and not rel.is_external:
            id_map[rId] = new.part.relate_to(rel._target, rel.reltype)
    for sh in src.shapes:
        el = copy.deepcopy(sh._element)
        for blip in el.iter(qn("a:blip")):
            emb = blip.get(qn("r:embed"))
            if emb in id_map: blip.set(qn("r:embed"), id_map[emb])
        new.shapes._spTree.append(el)
    return new

def set_by_marker(slide, marker, new_text):
    """Replace the text of the first shape containing `marker`, keeping run format."""
    for sh in slide.shapes:
        if sh.has_text_frame and marker.lower() in sh.text_frame.text.lower():
            p = sh.text_frame.paragraphs[0]
            if p.runs:
                p.runs[0].text = new_text
                for r in p.runs[1:]: r.text = ""
            else:
                p.add_run().text = new_text
            for extra in sh.text_frame.paragraphs[1:]:
                for r in extra.runs: r.text = ""
            return True
    return False
```

Duplicating a highlighter parallelogram specifically (don't build one
from `add_shape(MSO_SHAPE.PARALLELOGRAM, ...)` unless nothing on the
slide already has one to copy):

```python
def duplicate_shape_on_same_slide(slide, shape, new_left=None, new_top=None, new_width=None):
    """Clone a single shape (e.g. an existing highlighter) within its own slide."""
    el = copy.deepcopy(shape._element)
    slide.shapes._spTree.append(el)
    from pptx.shapes import Shape
    new_shape = slide.shapes[-1]
    if new_left is not None: new_shape.left = new_left
    if new_top is not None: new_shape.top = new_top
    if new_width is not None: new_shape.width = new_width  # height usually stays put
    return new_shape
```

Delete originals + Drive-strip:
```python
for sid in list(prs.slides._sldIdLst)[:N_TEMPLATE_SLIDES]:
    prs.slides._sldIdLst.remove(sid)
prs.save(dest)
# then zip-surgery: drop slideLayouts not referenced by any slide rel, and any
# ppt/media not referenced by a kept part; edit each master's <p:sldLayoutIdLst>
# and _rels to drop removed layouts; drop their [Content_Types] Overrides;
# reopen with python-pptx and force `s.slide_layout.name` to validate before
# overwriting the file (revert from a backup if it throws).
```

## Do not
- Do not build on a blank `Presentation()` and hand-draw the brand. That reads as
  off-template and invites colour mistakes (dark-on-dark).
- Do not put white-background charts on the dark closing/accent slides.
- Do not leave the unused example slides in the file; delete them.
- Do not insert a fresh parallelogram and guess its skew — duplicate
  an existing highlighter instance, or use `adj = 0.25` if you truly
  must build one from scratch.
- Do not let a highlighter parallelogram carry an outline, sit in
  front of its text, or cover more than one word/short phrase.
- Do not use `.odp` or PDF exports of any of these templates as the
  source file for this method.
