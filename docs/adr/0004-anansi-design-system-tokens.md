# ADR 0004 — Anansi Design System Token Adoption

## Status
Accepted

## Date
2025-07-15

## Context

The Vue 3 frontend (ADR 0003) initially used generic purple-blue accent colours (`#5b6af0`) with `20px` pill radii inherited from the vanilla-JS prototype. As the product matures and targets product-owner audiences, visual consistency and brand identity become important.

A formal design system was produced in `docs/design-system/DESIGN_SYSTEM.md`, specifying:
- A five-colour brand palette (Anansi Teal, Story Gold, Critical Amber, Deep Navy, Parchment White).
- Three typefaces: Raleway (headings), Inter (body), Fira Code (mono).
- Sharp geometric corners (4 px / 6 px radii) replacing pill-shaped buttons.
- A hexagonal spider motif for logos and icons.

Without a single, documented CSS-variable layer, colours and radii were scattered across the stylesheet, making future brand updates require grep-and-replace across many selectors.

## Decision

Adopt the Anansi Design System as the single source of truth for all frontend visual tokens.

All brand colours are defined once in the `:root` block as CSS custom properties:

| Token | Value | Usage |
|---|---|---|
| `--color-teal` | `#007B85` | Accent, focus rings, borders |
| `--color-gold` | `#F5A623` | Warning, Story Gold |
| `--color-amber` | `#D35400` | Danger, Critical Amber |
| `--color-navy` | `#2C3E50` | Light-mode text, Deep Navy |
| `--color-parchment` | `#F9F9F7` | Light-mode background |
| `--radius` | `4px` | Card, input, button corners |
| `--radius-lg` | `6px` | Modal, panel corners |

**Typography** is loaded via Google Fonts (`Raleway`, `Inter`, `Fira Code`) in `index.html`; CSS applies them through `--font-heading`, `--font-body`, `--font-mono` variables.

**Logo assets** (`public/favicon.svg`, `public/logo-spider.svg`) are source-of-truth SVGs inlined from `public/` at Vite build time; `AppHeader.vue` also carries an inline SVG for zero-FOUC header rendering.

## Consequences

### Positive
- Brand updates require changing a single `:root` declaration.
- Light / dark mode switching is implemented entirely through CSS variable overrides on `body.light-mode` — no JS color logic.
- WCAG contrast targets are met in both modes with the new palette.
- Sharp 4 px radii align the UI with the geometric hexagonal brand motif.

### Negative / Trade-offs
- The `#007B85` teal colour is hardcoded in SVG `fill` attributes (brand assets cannot use CSS variables). A future refactor could extract a `SpiderIcon.vue` component.
- Google Fonts introduces an external network dependency at page load; an offline-first deployment would need to bundle fonts locally.

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Keep generic purple-blue palette | No brand identity; inconsistent with design system |
| CSS-in-JS (e.g., `@emotion`) | Adds toolchain complexity; Vue SFCs + CSS variables are sufficient |
| Design-token build tool (Style Dictionary) | Overkill for a single-app deployment; plain CSS variables cover the use case |

## Related
- ADR 0003 — Vue 3 + Vite Frontend Migration
- `docs/design-system/DESIGN_SYSTEM.md`
- `frontend-vue/src/assets/styles.css`
- `frontend-vue/src/components/AppHeader.vue`
