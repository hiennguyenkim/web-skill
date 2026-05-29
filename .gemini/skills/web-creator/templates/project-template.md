# [Project Title]

A premium, modern web application built using HTML, Vanilla CSS, and JavaScript.

## 🎯 Project Vision
- **Core Value Proposition**: [Explain the main purpose and value of the web app]
- **Target Audience**: [Define who will use this application]
- **Key Experience Goal**: Establish a premium, highly-interactive, and wowed-at-first-sight user interface.

## 🎨 Design System & Visual Identity
We adhere to modern, premium aesthetics. No browser defaults are permitted.

### Colors
- **Theme**: Sleek Dark Mode (Primary) / Harmonious Light Mode (Optional)
- **Background**: [e.g., deep charcoal #0b0f19 or tailored HSL color]
- **Primary/Accent**: [e.g., vibrant indigo/violet gradient]
- **Secondary**: [e.g., emerald green or cyan for details]
- **Surface**: Glassmorphic cards with translucent border:
  ```css
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
  ```

### Typography
- **Headings**: Google Fonts `Outfit` or `Playfair Display` (serif)
- **Body**: Google Fonts `Inter` or `Plus Jakarta Sans`
- **Fallback**: System sans-serif

### Animations & Hover States
- **Transitions**: Smooth transitions on interactive elements (`transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1)`)
- **Micro-animations**: Fade-in and slide-up for content cards on page load, pulsing badges.
- **Hover effects**: Translate-y offset (`transform: translateY(-4px)`), glow shadow increase, gradient shift.

## 🛠️ Technology Stack & Architecture
- **Frontend Structure**: Semantic HTML5 (header, nav, main, section, article, footer, unique IDs for key elements)
- **Frontend Styling**: Modern CSS3 (CSS Custom Properties/Variables, CSS Grid, Flexbox, media queries for responsive layout)
- **Frontend Logic**: Vanilla ES6+ JavaScript (Modular structure, async API calls, interactive state management, fetch integration)
- **Backend Framework**: Node.js & Express.js (MVC architecture: server.js entrypoint, routes/, controllers/, middleware/, config/)
- **Database Layer**: MongoDB & Mongoose ORM (Schemas: models/User.js, models/Product.js, etc.)
- **Security & Session**: JWT (jsonwebtoken) authorization, Bcrypt.js password hashing, upload limits (multer)
- **Icons**: Lucide Icons or Google Fonts Material Symbols (SVG-based, never local image icon assets)

## 🔍 SEO & Accessibility Rules
- **SEO**:
  - Exactly one `<h1>` per page.
  - Descriptive meta title & description.
  - Descriptive `alt` tags on all images.
  - Open Graph meta tags.
- **Accessibility**:
  - Clear color contrast ratios (WCAG AA).
  - ARIA attributes where needed.
  - Semantic elements for screen readers.
