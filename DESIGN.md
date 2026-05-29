---
version: "alpha"
name: Obsidian Cyberpunk Rose Gold
description: A sleek, dark, glassmorphic visual identity combining rose gold elegance with cyber-cyan accents for multi-agent dashboards.
colors:
  primary: "#e0a96d"         # Rose Gold
  primary-dark: "#c58c50"    # Dark Rose Gold
  secondary: "#00f2fe"       # Cyber Cyan
  accent-green: "#00e676"    # Success Emerald
  accent-red: "#ff4b4b"      # Alert Crimson
  neutral-bg: "#08090c"      # Deep Dark Background
  neutral-panel: "rgba(17, 19, 25, 0.75)" # Glassmorphic Panel Background
  neutral-card: "#161920"    # Solid Card Background
  border: "rgba(255, 255, 255, 0.08)"
typography:
  h1:
    fontFamily: "Outfit, sans-serif"
    fontSize: "2.25rem"
    fontWeight: "850"
  h2:
    fontFamily: "Outfit, sans-serif"
    fontSize: "1.75rem"
    fontWeight: "700"
  body:
    fontFamily: "Inter, sans-serif"
    fontSize: "0.875rem"
    fontWeight: "400"
  code:
    fontFamily: "monospace"
    fontSize: "0.75rem"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  panel:
    backgroundColor: "{colors.neutral-panel}"
    border: "1px solid {colors.border}"
    backdropFilter: "blur(12px)"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral-bg}"
    rounded: "{rounded.md}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    border: "1px solid {colors.primary}"
    rounded: "{rounded.md}"
---

## Overview

Architectural Minimalism meets Cyberpunk Luxury. The design system leverages highly contrasting obsidian dark backdrops, transparent glass panels, and glowing borders of rose gold and cyan to construct a premium software development workspace.

---

## Colors

The system uses deep dark background tones overlaid with glowing gold-copper interactions and neon indicators.

* **Primary (#e0a96d):** Rose Gold. The brand's signature accent color. Used for headers, active text links, main buttons, and primary action hovers.
* **Secondary (#00f2fe):** Cyber Cyan. Used as secondary highlights, active status bars, loading loops, and special info callouts.
* **Neutral Background (#08090c):** A dark foundation with organic gradients of rose gold and cyan reflection overlays.
* **Neutral Panel (rgba(17, 19, 25, 0.75)):** High-transparency overlay containing `backdrop-filter: blur(12px)` and border highlights.

---

## Typography

Modern, crisp, geometric sans-serif fonts are preferred for clean alignment.

* **Outfit (Google Fonts):** Large headers, numbers, and system brand logotypes. Set to bold/black weight (`850`) for a premium impact.
* **Inter (Google Fonts):** Body, descriptions, and user inputs to maximize readability.
* **Monospace:** Code layouts, file paths, and terminal logs.

---

## Layout

A flexible layout powered by **Tailwind CSS Flexbox & CSS Grid**. 
* Margins and Paddings are mapped to the spacing scale (`{spacing.md}` or 16px).
* Panels are organized in semantic containers with glowing borders.

---

## Elevation & Depth

Visual depth is achieved through layering glass panels over glow gradients:
* **Background Layer:** Dark radial gradients.
* **Mid-ground Layer (Cards/Panels):** Semi-transparent black cards with blur and thin solid borders.
* **Active State:** Pulse glow shadows (`0 0 20px {colors.primary}`).

---

## Shapes

Soft, rounded interfaces promote modern premium aesthetics.
* **Small Elements (Inputs, Buttons):** Rounded md (`8px`).
* **Large Containers (Panels, Grid Cards):** Rounded xl (`16px`).

---

## Components

### primary-button
* **Style:** Solid background of `{colors.primary}`, dark text.
* **Interaction:** Hover scales up by 1.01% with shadow glow.

### glass-panel
* **Style:** Semi-transparent backdrops (`{colors.neutral-panel}`) with a thin 1px white border at 6% opacity.
