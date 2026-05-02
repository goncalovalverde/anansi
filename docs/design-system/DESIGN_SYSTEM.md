---
context: branding_and_ui_standards
project: Anansi
version: 1.0.0
last_updated: 2026-05-01
usage: "Refer to these HEX codes, font choices, and tone of voice for all frontend development and copywriting."
---
# Anansi Design System

**Vision:** Unweaving Complexity | Product Clarity

## 1. Brand Identity & Concept

The Anansi app is named after the West African "Lord of Stories" and trickster god. The design system bridges ancient narrative wisdom with modern product management. Visually, it focuses on "unweaving" the intricate web of a product backlog to provide clarity to the Product Owner.

### Logo Variations

* **System Logo:** Used for high-level documentation, READMEs, and the main landing page. Includes the wordmark and tagline.
* **In-App Logo:** A streamlined version for the dashboard header.
* **Favicon:** A high-contrast geometric representation of a web or the letter 'A' for browser tabs.

---

## 2. Color Palette

These colors should be implemented as CSS variables or within a Tailwind configuration to ensure consistency.

| Usage                | Color Name      | HEX Code    | Purpose                                       |
| :------------------- | :-------------- | :---------- | :-------------------------------------------- |
| **Primary**    | Anansi Teal     | `#007B85` | Main brand color, buttons, and navigation.    |
| **Action**     | Story Gold      | `#F5A623` | Warnings, highlights, and "trickster" alerts. |
| **Alert**      | Critical Amber  | `#D35400` | Roadmap blockers or high-priority items.      |
| **Neutral**    | Deep Navy       | `#2C3E50` | Primary text and sidebar backgrounds.         |
| **Background** | Parchment White | `#F9F9F7` | Main app background; easy on the eyes         |

### CSS Variable Implementation

```css
:root {
  --color-primary: #007B85;
  --color-accent: #F5A623;
  --color-alert: #D35400;
  --color-neutral: #2C3E50;
  --color-bg: #F9F9F7;
}
```

### 2.1 Visual Reference

- **Full Logo (README):** Refer to `watermarked_img_15582639535341018290.png` for the layout containing the "Anansi Logo System" title and the updated "Unweaving Complexity" tagline.
- **In-App Logo:** Refer to the "In-App Logo" variant in the same image for header placement.
- **Favicon:** Refer to the circular "A" web-icon variant for browser tab implementation.

## 3. Typography

The typography should balance the "Lord of Stories" authority with "Product Clarity" precision.

* **Headings (Wordmark):** **Montserrat** or  **Raleway** . Bold, geometric sans-serif to match the logo’s line weight.
* **Body Text:** **Inter** or  **Roboto** . Optimized for high-density data reading in backlogs and roadmaps.
* **Monospace:**  **Fira Code** . For any technical product metadata or implementation details.

## 4. UI / UX Principles

**Geometric Precision**

* ****Borders:** Use thin, sharp borders (1px) in `Deep Navy` or `Anansi Teal`**
* **Shapes:** Prefer hexagonal or sharp-cornered containers over rounded "pill" shapes to maintain the web/spider theme

**Voice and Tone**

* **Language:** The primary language is English
* **Tone:** Professional, sharp, and insightful. Avoid fluff

## 5. Folder Structure Reference

Keep all assets organized in the following directory for Copilot and development reference:

**Plaintext**

```
/development
  /docs
    /design-system
      /brand       <-- Logo exports (SVG/PNG)
      /icons       <-- Custom UI icons
      DESIGN_SYSTEM.md  <-- This file
```


## 6. Iconography Strategy

All icons should be linear with a weight of 1.5pt to 2pt, mirroring the complexity of threads being woven into a story

* **Spider/Web motifs:** Use for "connections" or "dependencies".
* **Path motifs:** Use for "roadmaps" and "milestones"
