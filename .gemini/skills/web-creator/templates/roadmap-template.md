# Project Roadmap

## 🗓️ Phase 1: Research, Spec & Discovery
- [ ] Define precise product features and user flows (`PROJECT.md` & `REQUIREMENTS.md`)
- [ ] Research UI/UX design trends (colors, gradients, glassmorphism setup)
- [ ] Outline component structure and key interactive moments

## 🎨 Phase 2: Theme & Foundation
- [ ] Create base HTML structure (`index.html`) with Google Fonts import and script/CSS linkings.
- [ ] Write `index.css` setup:
  - [ ] CSS resets & box-sizing
  - [ ] CSS Custom Properties (colors, gradients, margins, transitions)
  - [ ] Global typography settings
  - [ ] Standard utility classes (glass card, primary button, container, layout grids)
  - [ ] Core animation keyframes (`@keyframes fadeIn`, `@keyframes slideUp`)

## 🧱 Phase 3: Core Components & Layout
- [ ] Implement Responsive Navigation Bar (glassmorphic or solid transition, mobile toggle)
- [ ] Build Hero Section (eye-catching gradient text, animated background blobs, call-to-actions)
- [ ] Build Feature/Content Grid (glassmorphic cards, custom SVGs/icons, hover offsets)
- [ ] Build interactive widgets or secondary blocks (pricing cards, testimonials slider, contact form)
- [ ] Implement footer with sitemap and copyright

## ⚙️ Phase 4: Backend & Database Integration
- [ ] Initialize Node.js dependencies (`express`, `mongoose`, `dotenv`, `cors`, `jsonwebtoken`, `bcryptjs`) in `package.json`
- [ ] Establish database connection utility (`config/db.js`) and environment credentials (`.env`)
- [ ] Implement Mongoose database schemas (`User.js`, `Product.js`, `Category.js`, `Collection.js`, `Order.js`, `Coupon.js`, `Review.js`, `ContactMessage.js`, `Consultation.js`, `SiteSetting.js`) in `models/`
- [ ] Implement secure Express API routes and authentication/role middlewares in `routes/` and `middleware/`
- [ ] Implement controller business logic for standard CRUD operations, customer forms, user auth, and consultation processing in `controllers/`
- [ ] Connect main server entrypoint (`server.js`) to serve the static frontend and mount all API routes

## ⚡ Phase 5: Frontend JS & API Connection
- [ ] Implement DOM loading event, navigation toggles, page dynamic state management, and active styling
- [ ] Connect frontend forms (Login, Register, Contact, Consultation) to backend API endpoints
- [ ] Connect product listing filters (by category, brand, skin type, function) to the dynamic product API
- [ ] Integrate local storage cart and user state with API-based ordering and wishlist endpoints
- [ ] Add trigger-based micro-animations (fade-in, slide-up, scroll reveals) and loading states

## 🚀 Phase 6: Refinement, SEO & QA Polish
- [ ] Add SEO tags (meta description, viewport, Open Graph, single `<h1>`)
- [ ] Audit responsive layouts on Mobile, Tablet, and Desktop
- [ ] Ensure all assets are loaded properly (no placeholders, run `generate_image` for illustrations)
- [ ] Verify accessibility compliance (WCAG contrast, focus indicators)
- [ ] Run automated Playwright user-flow verification and output test report
