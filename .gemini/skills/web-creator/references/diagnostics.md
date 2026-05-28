# Diagnostic Checklist & Code-Saving Patterns

Follow these guidelines strictly to build clean, premium, and error-free web code.

---

## 🛑 1. PREVENTING BROKEN IMAGE PATHS (Asset Fails)
- **Problem**: AI-generated code often uses dead placeholder URLs (like `via.placeholder.com` which is deprecated) or links to local files that don't exist.
- **Rule**:
  - For UI icons, logos, and badges: **NEVER** use image files. Always use **inline SVGs** (with proper `width`, `height`, and `fill/stroke` attributes) or SVG-based Google Fonts Material Symbols.
  - For illustrations and backgrounds: Trigger the `generate_image` tool to build actual image assets, save them in the `assets/` folder, and link them using relative paths (e.g. `./assets/hero.jpg`).

---

## 🎨 2. GOOGLE FONTS IMPORT RULES (Style Fails)
- **Problem**: Google Fonts imports (`@import url(...)`) are ignored by browsers if they are not the absolute first lines in the CSS file.
- **Rule**:
  - `@import` statements **MUST** be at the very top of `index.css` (line 1-3).
  - No CSS resets, variables, or comments should appear before the `@import` statements.

---

## 📱 3. PREVENTING MOBILE VIEWPORT OVERFLOW (Layout Fails)
- **Problem**: Horizontal scrollbars appearing on mobile devices because of fixed width properties (e.g., `width: 800px;` or `margin: 50px;` without box-sizing).
- **Rule**:
  - Always apply `box-sizing: border-box;` globally:
    ```css
    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    ```
  - **NEVER** use fixed `width` on containers. Use `width: 100%;` with `max-width: [size]px;`.
  - Use relative spacing units (`rem`, `vh`, `vw`) and CSS Flexbox/Grid for flexible layout grids.
  - Use `overflow-x: hidden;` on the `body` and wrapper container as a safety shield.

---

## ⚡ 4. ELIMINATING JAVASCRIPT RUNTIME CRASHES (Script Fails)
- **Problem**: JavaScript executing before the browser finishes parsing the HTML DOM, leading to `TypeError: Cannot read properties of null (reading 'addEventListener')`.
- **Rule**:
  - Wrap all interactive element selection and event listener binding inside a `DOMContentLoaded` event listener:
    ```javascript
    document.addEventListener('DOMContentLoaded', () => {
      // DOM selection & event listeners go here
    });
    ```
  - Always use **optional chaining** (`?.`) or safety checks when adding event listeners to elements that might be dynamic or page-specific:
    ```javascript
    const toggleButton = document.querySelector('#menu-toggle');
    toggleButton?.addEventListener('click', toggleMenu);
    ```

---

## 👁️ 5. CONTRAST & ACCESSIBILITY AUDITING (Aesthetic Fails)
- **Problem**: Text that is hard to read because the color contrast between background and text is too low (e.g. gold text on light pink, or dark grey text on black).
- **Rule**:
  - Ensure all text elements meet WCAG AA contrast standards (minimum contrast ratio of 4.5:1 for normal text, 3:1 for large text).
  - Define high-contrast text color variables in the CSS root corresponding to their backgrounds:
    - Dark Obsidian backgrounds (`#0a0b0e`) must use white/light gray (`#faf5f5` or `#e2e8f0`) for body copy and high-value accents (`#e5c3b2`) for headings.
