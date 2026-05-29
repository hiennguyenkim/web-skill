# Build Your Own Web App (Step-by-Step Guide)

Inspired by the CodeCrafters `build-your-own-x` compilation, this guide walks you through using our autonomous Web AI Platform to build, verify, and host your own custom fullstack application from scratch.

Our platform supports generating:
* **Frontend**: Responsive semantic HTML5, CSS Grid layouts, interactive vanilla JS.
* **Backend**: Express.js REST APIs, Mongoose/MongoDB schemas and routes, authentication middlewares.
* **Testing & Security**: Automated Playwright verification scripts, static SAST security scan audits.

---

## 🛠️ What You Will Build
In this tutorial, we will build a **Premium E-Commerce Cosmetics Store** featuring:
1. A gorgeous glassmorphic storefront.
2. A REST API for product catalogs.
3. User authorization & MongoDB database schemas.
4. Self-healing browser testing verification.

---

## 🏁 Step 1: Formulate Your Application Spec (Concept)

The Product Manager (PM) Agent needs a business requirements description (Concept). Write a clear specification file or text describing your target application. 

Here is our cosmetics store requirement spec:
> A responsive cosmetics storefront named "GlowStore" themed "Obsidian Rose Gold". 
> It requires a navigation bar, a hero header, a product showcase grid, and a contact form.
> The backend should expose an Express.js API with Mongoose schemas for Products (`name`, `price`, `image`, `description`) and Users (`username`, `password`, `email`), user authentication, and static asset routes.

---

## 🤖 Step 2: Initialize the Project and Generate the Backlog

We can initialize this project either via the **PO Dashboard GUI** (`http://localhost:8000/`) or directly via the **Command Line (CLI)**.

### Option A: Using the PO Dashboard (GUI)
1. Boot the server: `python cli.py serve --port 8000`
2. Open `http://localhost:8000/` and navigate to the **Control Center**.
3. Under **Tạo dự án mới**, enter **Tên dự án** (`GlowStore`) and paste the requirement concept. Click **Tạo specs**.
4. Head to **Agile Backlog** and click **Generate Backlog (AI)**. The Product Owner agent will write the user stories.
5. Click **Prioritize & Estimate (MoSCoW/Fibonacci)** to automatically prioritize the backlog.

### Option B: Using the CLI
Execute direct spec generation:
```bash
python cli.py build "GlowStore" "A responsive cosmetics storefront named GlowStore..." --workspace "d:/ai-web-skill/projects/glowstore"
```

---

## 🧱 Step 3: Run the Autonomous Multi-Agent Build Pipeline

Once the requirements and stories are ready, we trigger the multi-agent generation loop:

1. Click **Kích hoạt build 6 Pha** in the dashboard.
2. The platform coordinates 6 specialized agents to assemble your application:
   * **Phase 1 (Designer Agent)**: Configures typography and HSL CSS color variables.
   * **Phase 2 (Coder Agent)**: Generates semantic HTML5 structure with unique testing IDs.
   * **Phase 3 (CSS Architect)**: Upgrades the layout using CSS Grid, responsive media queries, and animations.
   * **Phase 4 (Backend Developer)**: Writes complete Node.js Express server routes, mongoose schemas, auth middlewares, and `package.json`.
   * **Phase 5 (QA Specialist)**: Runs automated Playwright tests to check for script crashes or overflows. If errors occur, the **Forensics Agent** applies self-healing patches automatically.
   * **Phase 6 (Security Agent)**: Executes a SAST security scan to audit input validations.

---

## 🧪 Step 4: Audit Reports & Live Preview

When the progress bar shows `PASSED`:

1. **Test Logs**: Click **Xem Playwright Report HTML** to view browser logs and console outputs.
2. **Security Logs**: Click **Xem Security Report MD** to view static analysis results.
3. **Live Preview**: Click **Mở ứng dụng Live Preview** to launch and interact with your newly created fullstack app directly in the browser!

---

## 🚀 Step 5: Hosting Your Generated App

Your generated code files are located in your workspace directory (e.g. `d:/ai-web-skill/projects/glowstore`).

To host the generated application:
1. Navigate to the project folder:
   ```bash
   cd d:/ai-web-skill/projects/glowstore
   ```
2. Install the generated backend dependencies:
   ```bash
   npm install
   ```
3. Start the Express server:
   ```bash
   npm start
   ```
   Your custom app is now running and connected to MongoDB!
