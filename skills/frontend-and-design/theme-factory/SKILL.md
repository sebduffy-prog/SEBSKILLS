---
name: theme-factory
category: frontend-and-design
description: >
  Toolkit for styling artifacts with a theme. These artifacts can be slides,
  docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with
  colors/fonts that you can apply to any artifact that has been creating, or
  can generate a new theme on-the-fly.
when_to_use:
  - Applying consistent, professional styling (colors + fonts) to a slide deck or presentation
  - Styling docs, reports, or HTML landing pages with a cohesive theme
  - Choosing from 10 pre-set themes (Ocean Depths, Sunset Boulevard, Tech Innovation, etc.) via the theme-showcase.pdf
  - Generating a new custom theme on-the-fly when none of the pre-set themes fit
  - Ensuring proper contrast, readability, and a consistent visual identity across all slides of an artifact
when_not_to_use:
  - Building a full frontend interface or web app from scratch — use frontend-design instead
  - Adding a light/dark mode switcher — use theme-toggle
  - Creating charts or dashboards where chart-specific palettes matter — use dataviz
  - Shipping a visual change without user preview/approval — pair with design-approval-gate
keywords:
  - theme
  - styling
  - color palette
  - hex codes
  - font pairing
  - typography
  - slide deck
  - presentation
  - landing page
  - branding
  - visual identity
  - theme showcase
  - custom theme
  - contrast
  - readability
similar_to:
  - frontend-design
  - theme-toggle
  - brand-guidelines
  - design-approval-gate
inputs_needed:
  - The artifact to style (slides, doc, report, or HTML page)
  - The user's theme choice after viewing theme-showcase.pdf (explicit confirmation required)
  - For a custom theme, a basic description of the desired look/feel to pick colors and fonts
produces: An artifact (deck, doc, or page) styled with a chosen theme's colors and font pairings applied consistently throughout
status: stable
owner: seb.duffy
updated: 2026-07-10
license: Complete terms in LICENSE.txt
---


# Theme Factory Skill

This skill provides a curated collection of professional font and color themes themes, each with carefully selected color palettes and font pairings. Once a theme is chosen, it can be applied to any artifact.

## Purpose

To apply consistent, professional styling to presentation slide decks, use this skill. Each theme includes:
- A cohesive color palette with hex codes
- Complementary font pairings for headers and body text
- A distinct visual identity suitable for different contexts and audiences

## Usage Instructions

To apply styling to a slide deck or other artifact:

1. **Show the theme showcase**: Display the `theme-showcase.pdf` file to allow users to see all available themes visually. Do not make any modifications to it; simply show the file for viewing.
2. **Ask for their choice**: Ask which theme to apply to the deck
3. **Wait for selection**: Get explicit confirmation about the chosen theme
4. **Apply the theme**: Once a theme has been chosen, apply the selected theme's colors and fonts to the deck/artifact

### No local bundle? (remote use)

If `theme-showcase.pdf` and the `themes/` directory are not present locally (e.g. running from the SKILL.md text alone), fetch the bundled files with `curl -fsSL` or WebFetch from:

`https://raw.githubusercontent.com/sebduffy-prog/SebDuffy/main/skills/frontend-and-design/theme-factory/<relative-path>`

Bundled files (all payload lives here — SKILL.md carries none): `theme-showcase.pdf`, plus one file per theme under `themes/`: `arctic-frost.md`, `botanical-garden.md`, `desert-rose.md`, `forest-canopy.md`, `golden-hour.md`, `midnight-galaxy.md`, `modern-minimalist.md`, `ocean-depths.md`, `sunset-boulevard.md`, `tech-innovation.md`.

## Themes Available

The following 10 themes are available, each showcased in `theme-showcase.pdf`:

1. **Ocean Depths** - Professional and calming maritime theme
2. **Sunset Boulevard** - Warm and vibrant sunset colors
3. **Forest Canopy** - Natural and grounded earth tones
4. **Modern Minimalist** - Clean and contemporary grayscale
5. **Golden Hour** - Rich and warm autumnal palette
6. **Arctic Frost** - Cool and crisp winter-inspired theme
7. **Desert Rose** - Soft and sophisticated dusty tones
8. **Tech Innovation** - Bold and modern tech aesthetic
9. **Botanical Garden** - Fresh and organic garden colors
10. **Midnight Galaxy** - Dramatic and cosmic deep tones

## Theme Details

Each theme is defined in the `themes/` directory with complete specifications including:
- Cohesive color palette with hex codes
- Complementary font pairings for headers and body text
- Distinct visual identity suitable for different contexts and audiences

## Application Process

After a preferred theme is selected:
1. Read the corresponding theme file from the `themes/` directory
2. Apply the specified colors and fonts consistently throughout the deck
3. Ensure proper contrast and readability
4. Maintain the theme's visual identity across all slides

## Create your Own Theme
To handle cases where none of the existing themes work for an artifact, create a custom theme. Based on provided inputs, generate a new theme similar to the ones above. Give the theme a similar name describing what the font/color combinations represent. Use any basic description provided to choose appropriate colors/fonts. After generating the theme, show it for review and verification. Following that, apply the theme as described above.
