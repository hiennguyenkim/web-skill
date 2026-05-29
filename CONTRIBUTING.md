# Contributing to Web AI Platform

Thank you for your interest in contributing to the Web AI Platform! As a multi-agent system combining MCP skills, a Product Owner dashboard, and automated tests, we appreciate contributions of all kinds: bug fixes, new features, new MCP skills, documentation improvements, and bug reports.

---

## 1. Code of Conduct

By participating in this project, you agree to maintain a respectful, inclusive, and professional environment for all contributors.

---

## 2. Getting Started

### Prerequisites
* Python 3.10 or higher
* Node.js 18 or higher
* Redis (for Celery broker)

### Local Dev Setup
1. **Fork and Clone** the repository:
   ```bash
   git clone https://github.com/your-username/ai-web-skill.git
   cd ai-web-skill
   ```
2. **Install Python dependencies** and setup pre-commit hooks:
   ```bash
   pip install -r requirements.txt
   pip install pre-commit
   pre-commit install
   ```
3. **Install Frontend dependencies**:
   ```bash
   cd apps/po_dashboard
   npm install
   ```

---

## 3. Style & Quality Guidelines

We enforce strict formatting rules to keep the codebase clean:
* **Python**: We use `black` for formatting and `ruff` / `isort` for linting and import ordering. The pre-commit hooks will automatically format and validate these on each commit.
* **Frontend**: Write clean React + TypeScript components in `apps/po_dashboard`. Ensure no typescript compiler warnings remain.
* **CSS & HTML**: Maintain separation of concerns. Do not mix inline styling or `<style>` blocks in generated code; define modular design variables in `DESIGN.md`.

---

## 4. How to Write and Run Tests

Before submitting any Pull Request, you must verify that all unit and integration tests pass successfully:

```bash
# Run the pytest test suite
python -m pytest -v tests/
```

If you add a new MCP Skill, you **must** write a corresponding unit test under its `tests/` folder mocking the LLM API calls. Refer to [tests/unit/test_po_toolkit.py](file:///d:/ai-web-skill/tests/unit/test_po_toolkit.py) for examples.

---

## 5. Adding New MCP Skills

If you are developing a new skill:
1. Create a sub-folder under `skills/` (e.g. `skills/my_new_skill`).
2. Write a FastMCP server and expose capabilities with the `@tool` decorator.
3. Document how to register it in `docs/CREATING_SKILLS.md`.

---

## 6. Pull Request Process

1. Create a branch for your feature or bug fix:
   ```bash
   git checkout -b feature/my-amazing-feature
   ```
2. Make your changes, ensure they conform to formatting styles, and run tests.
3. Commit and push:
   ```bash
   git commit -m "feat: add support for skill-x"
   git push origin feature/my-amazing-feature
   ```
4. Open a Pull Request against the `main` branch. Provide a clear description of what the PR accomplishes and reference any related issues.
