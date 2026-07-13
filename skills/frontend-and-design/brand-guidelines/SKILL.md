---
name: brand-guidelines
description: Applies Anthropic's official brand colors and typography to any sort of artifact that may benefit from having Anthropic's look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply.
license: Complete terms in LICENSE.txt
category: frontend-and-design
when_to_use:
  - Applying Anthropic's official brand colours and typography to an artifact
  - Giving a doc, slide, or page the Anthropic look-and-feel
  - Enforcing company design standards or visual formatting
  - Smart font application and text/shape/accent-colour styling
when_not_to_use:
  - Applying the VCCP brand system — use vccp-media-design
  - Generic on-the-fly themes for any artifact — use theme-factory
  - Building a reusable colour token system — use brand-color-token-system
keywords:
  - anthropic
  - brand
  - brand colors
  - typography
  - styleguide
  - look and feel
  - fonts
  - brand styling
  - visual identity
  - design standards
  - accent colors
similar_to:
  - vccp-media-design
  - theme-factory
  - brand-color-token-system
inputs_needed: The artifact to style and which elements (colours, fonts, accents) need Anthropic branding.
produces: The artifact restyled with Anthropic's official colours and typography.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Anthropic Brand Styling

## Overview

To access Anthropic's official brand identity and style resources, use this skill.

**Keywords**: branding, corporate identity, visual identity, post-processing, styling, brand colors, typography, Anthropic brand, visual formatting, visual design

## Brand Guidelines

### Colors

**Main Colors:**

- Dark: `#141413` - Primary text and dark backgrounds
- Light: `#faf9f5` - Light backgrounds and text on dark
- Mid Gray: `#b0aea5` - Secondary elements
- Light Gray: `#e8e6dc` - Subtle backgrounds

**Accent Colors:**

- Orange: `#d97757` - Primary accent
- Blue: `#6a9bcc` - Secondary accent
- Green: `#788c5d` - Tertiary accent

### Typography

- **Headings**: Poppins (with Arial fallback)
- **Body Text**: Lora (with Georgia fallback)
- **Note**: Fonts should be pre-installed in your environment for best results

## Features

### Smart Font Application

- Applies Poppins font to headings (24pt and larger)
- Applies Lora font to body text
- Automatically falls back to Arial/Georgia if custom fonts unavailable
- Preserves readability across all systems

### Text Styling

- Headings (24pt+): Poppins font
- Body text: Lora font
- Smart color selection based on background
- Preserves text hierarchy and formatting

### Shape and Accent Colors

- Non-text shapes use accent colors
- Cycles through orange, blue, and green accents
- Maintains visual interest while staying on-brand

## Technical Details

### Font Management

- Uses system-installed Poppins and Lora fonts when available
- Provides automatic fallback to Arial (headings) and Georgia (body)
- No font installation required - works with existing system fonts
- For best results, pre-install Poppins and Lora fonts in your environment

### Color Application

- Uses RGB color values for precise brand matching
- Applied via python-pptx's RGBColor class
- Maintains color fidelity across different systems

## Deliverable

This skill must produce a **restyled artifact file on disk**, not a description of what branding to apply. Save the branded output to a concrete path — the same file re-styled in place, or a new copy alongside it (e.g. `<name>-anthropic-brand.pptx` / `.docx` / `.html`). When the request is to codify the system rather than style one artifact, ship a runnable helper (e.g. `anthropic_brand.py` applying the RGBColor/font rules above) so the palette and typography are reusable.

Final verify step: confirm the file exists, opens without error, and spot-check that the brand colours (`#141413`, `#d97757`, etc.) and Poppins/Lora fonts actually landed on headings, body, and accent shapes.

If the source artifact is missing, ship the scaffold anyway — a styled template or the brand-application script with an "awaiting artifact" placeholder — never end with brand values narrated only in chat.
