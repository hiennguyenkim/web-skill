# BeautyStore Landing Page

A premium, modern e-commerce storefront landing page for organic beauty products.

## 🎯 Project Vision
- **Core Value Proposition**: Showcase high-end, organic skincare products with an immersive, high-aesthetic landing page that maximizes customer engagement and conversion.
- **Target Audience**: Connoisseurs of organic, luxury beauty and skincare products.
- **Key Experience Goal**: Establish a premium visual layout with smooth transitions, glassmorphic cards, and curated product visuals to immediately wow the visitor.

## 🎨 Design System & Visual Identity
We adhere to modern, premium aesthetics. No browser defaults are permitted.

### Colors
- **Theme**: Sleek Dark Rose Mode
- **Background**: Deep obsidian background with a subtle rose tint (`#0f0a0d`)
- **Primary/Accent**: Vibrant rose gold gradient (`linear-gradient(135deg, #e5a9a9 0%, #b76e79 100%)`)
- **Secondary**: Soft pearl white (`#f4eded`)
- **Surface**: Translucent glassmorphic panels:
  ```css
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 10px 40px 0 rgba(0, 0, 0, 0.5);
  ```

### Typography
- **Headings**: Google Fonts `Outfit` (bold, spacious tracking)
- **Body**: Google Fonts `Inter` (high readability, subtle line-height)
- **Fallback**: System sans-serif

### Animations & Hover States
- **Transitions**: Smooth easing (`transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1)`)
- **Micro-animations**: Pulse effects on cart badges, slow-floating decorative blur circles in the background, fade-in-up entries for content grids.
- **Hover effects**: Products scaling up slightly (`transform: scale(1.03)`), buttons filling with a glow, link underlines expanding from center.

## 🛠️ Technology Stack & Architecture
- **Structure**: Semantic HTML5 (header, main, section, article, footer, unique IDs for testing)
- **Styling**: Vanilla CSS3 (Custom variables, CSS Grid, Flexbox, media queries for mobile-first responsiveness)
- **Logic**: Vanilla ES6+ JavaScript (Dynamic cart management, product filtering, interactive FAQ accordions)
- **Icons**: Lucide SVG Icons embedded inline

## 🔍 SEO & Accessibility Rules
- **SEO**:
  - Exactly one `<h1>` per page (Hero title).
  - Title: "Aura Skincare | Luxury Organic Beauty"
  - Meta Description: "Experience the pure essence of luxury skincare with Aura's organic collection. Shop our premium, naturally sourced moisturizers, serums, and oils."
- **Accessibility**:
  - Accessible focus outlines.
  - ARIA expanded states for mobile nav menu.
