# Architecture Audit Report
**Repository:** `hiennguyenkim/web-skill`  
**Audit Date:** 2026-05-30  
**Auditor Role:** Principal Software Architect / Staff Engineer  
**Audit Scope:** Full platform readiness assessment for evolution from AI Website Generator → AI Engineering Platform

---

## Executive Summary

The repository is at an **inflection point**. It began as a single-purpose AI website generator. Through recent sprints, foundational platform primitives have been introduced (`platform_core/core/`). However, the application layer (`apps/web_creator/`) continues to carry significant architectural debt from its origin.

**Overall Platform Readiness Score: 5.8 / 10**

The platform has the right *ideas* but not yet the right *boundaries*. Platform primitives exist but are not consistently enforced. The product layer (web_creator) still bypasses several platform contracts.

---

## 1. Current Architecture — As-Built

```
hiennguyenkim/web-skill/
│
├── platform_core/core/           ← Platform Layer (emerging)
│   ├── environment/              ✅ Interface + LocalEnvironment (sandbox)
│   ├── artifacts/                ✅ Artifact + ArtifactManager
│   ├── decisions/                ✅ Decision + DecisionManager
│   ├── events/                   ✅ Event + EventManager
│   ├── workflow/                 ✅ WorkflowEngine (topological sort)
│   ├── registry/                 ✅ CapabilityRegistry (10 defaults)
│   ├── llm/                      ⚠️  LLMClient (thin wrapper, leaks provider config)
│   └── skill_sdk/                ⚠️  SkillServer (thin FastMCP wrapper)
│
├── apps/
│   ├── web_creator/              ← Product Layer (God Application)
│   │   └── app/
│   │       ├── agents/
│   │       │   ├── base.py       ❌ Duplicates LLMClient logic
│   │       │   ├── personas.py   ⚠️  7 agent classes, hardcoded system prompts
│   │       │   └── coordinator.py ❌ God Object (882 lines)
│   │       ├── db/
│   │       │   ├── models.py     ⚠️  7 SQLAlchemy models, mixed concerns
│   │       │   ├── database.py   ⚠️  Hardcoded path resolution
│   │       │   └── auth.py       OK
│   │       ├── mcp/server.py     ⚠️  MCP tools bypass platform
│   │       ├── main.py           ❌  679-line God Router (Auth + Build + PO + Chat)
│   │       └── worker.py         ⚠️  Celery worker, direct DB access on failure
│   │
│   └── po_dashboard/             ← Frontend Product (React/Vite)
│       └── src/
│           └── App.tsx           ❌ 1818-line God Component
│
├── skills/                       ← MCP Skill Servers (partially bypassed)
│   ├── html_coder/server.py      ⚠️  Skill exists but not called via Registry
│   ├── css_expert/server.py      ⚠️  Same
│   ├── backend_generator/        ⚠️  Same
│   ├── qa_playwright/server.py   ❌ Uses raw subprocess, bypasses Environment
│   └── po_toolkit/server.py      ⚠️  Called directly from main.py
│
├── tests/
│   ├── unit/                     ✅ 36 tests, 100% pass rate
│   └── integration/              ⚠️  Only 3 integration tests
│
├── cli.py                        ⚠️  sys.path manipulation, fragile
├── requirements.txt              ⚠️  No pinned versions (security risk)
├── .github/workflows/ci.yml      ❌ CI fails (missing API keys, redis)
└── docker-compose.yml            ⚠️  Redis configured but not production-ready
```

---

## 2. Dependency Graph

```
                        ┌─────────────────────────────┐
                        │        cli.py               │
                        │   (sys.path manipulation)   │
                        └──────────┬──────────────────┘
                                   │
                    ┌──────────────┼──────────────────────┐
                    │              │                       │
            ┌───────▼──────┐  ┌───▼──────┐  ┌────────────▼──────┐
            │  app/main.py │  │ mcp/     │  │  worker.py        │
            │  (FastAPI)   │  │ server.py│  │  (Celery)         │
            └──────┬───────┘  └────┬─────┘  └────────┬──────────┘
                   │               │                  │
           ┌───────▼───────────────▼──────────────────▼──────────┐
           │              AgentCoordinator (GOD OBJECT)           │
           │              apps/web_creator/app/agents/coordinator │
           └───┬──────┬──────┬──────┬──────┬──────┬──────┬───────┘
               │      │      │      │      │      │      │
            PMAgent Designer Coder CSS QA Security Backend Architect
               │      │      │      │   │      │      │       │
               └──────┴──────┴──────┴───┴──────┴──────┴───────┘
                                   │
                              BaseAgent
                           (base.py line 2:
                         import google.generativeai ← DEPRECATED)
                                   │
                        ┌──────────┴───────────┐
                        │  Hardcoded LLM Call  │
                        │  Bypasses LLMClient  │  ← VIOLATION
                        └──────────────────────┘

platform_core/core/           ← Used for: env, artifacts, decisions, events
                                  NOT used for: LLM routing in BaseAgent
                                  NOT used for: skills dispatch
```

**Critical Dependency Violations:**
1. `BaseAgent` (`base.py`) directly imports `google.generativeai` and `openai` — bypassing `LLMClient`
2. `AgentCoordinator` calls agents' `call_llm()` directly — bypassing Capability Registry
3. `skills/qa_playwright/server.py` calls `subprocess.run()` directly — bypassing `Environment`
4. `app/main.py` imports `skills/po_toolkit/server.py` functions directly — bypassing any abstraction
5. `mcp/server.py` constructs `AgentCoordinator` inline — no dependency injection

---

## 3. Subsystem Scores

### 3.1 Environment Layer
**Score: 7.5 / 10**

**Strengths:**
- ✅ Clean `Environment` ABC with `read_file`, `write_file`, `exists`, `list_dir`, `run_command`, `delete_file`
- ✅ `LocalEnvironment` implements sandbox via `commonpath` check — correctly raises `PermissionError`
- ✅ Used consistently by `AgentCoordinator`

**Problems:**
- ❌ `skills/qa_playwright/server.py` uses `subprocess.run()` directly (lines 67-73) — **Environment contract broken**
- ❌ `skills/qa_playwright/server.py` uses `open()` directly (lines 63-64) — **Environment contract broken**
- ❌ `app/main.py` uses `os.makedirs()` directly (line 39)
- ⚠️  `Environment` has no `make_dir()` method — callers fall back to `os.makedirs()`
- ⚠️  No `RemoteEnvironment` or `DockerEnvironment` implementation yet
- ⚠️  `run_command` has no timeout parameter

**Refactor Priority:** Medium — interface is correct, compliance is the gap.

---

### 3.2 Artifact System
**Score: 7.0 / 10**

**Strengths:**
- ✅ `Artifact` has: `id`, `project_id`, `type`, `version`, `producer`, `status`, `content`, `metadata`, `created_at`
- ✅ `ArtifactManager` filesystem-backed — no DB dependency
- ✅ `parent_artifact` field enables DAG tracing
- ✅ Used by `AgentCoordinator` at every major output

**Problems:**
- ❌ `content` is `Any` — no schema validation, no type safety
- ❌ No `ArtifactStore` interface — only `ArtifactManager` concrete class; cannot mock for remote storage
- ❌ Artifacts are scoped to *workspace* — no global project-level artifact index
- ⚠️  `status` field is free-form string (`"COMPLETED"`) — not an Enum
- ⚠️  No versioning strategy — `version = "1.0.0"` is static
- ⚠️  `created_at` still uses deprecated `datetime.datetime.utcnow()`

**Refactor Priority:** Medium — functional but needs contract hardening.

---

### 3.3 Decision System
**Score: 6.5 / 10**

**Strengths:**
- ✅ `Decision` links to `artifact_id` — traceability exists
- ✅ Filesystem-backed `DecisionManager`
- ✅ `AgentCoordinator` logs a decision at every major step

**Problems:**
- ❌ `decision` field is a plain string — should be a typed `DecisionType` Enum (e.g., `ARCHITECTURE_CHOICE`, `AGENT_SELECTION`, `REPAIR_STRATEGY`)
- ❌ No `DecisionStore` interface — only concrete `DecisionManager`
- ❌ Decisions not linked to `Event` IDs — timeline correlation is manual
- ❌ No **ADR (Architecture Decision Record)** generation — architect decisions not formalized
- ⚠️  `reason` and `decision` fields are semantically overlapping
- ⚠️  Missing `confidence_score`, `alternatives_considered` fields

**Refactor Priority:** Medium — usable but semantically thin.

---

### 3.4 Event System
**Score: 7.0 / 10**

**Strengths:**
- ✅ `Event` has: `id`, `type`, `producer`, `project_id`, `payload`, `timestamp`
- ✅ `EventManager.emit_event()` writes JSON + updates manifest
- ✅ 12 event types emitted across build lifecycle
- ✅ `WorkflowEngine` emits 6 additional stage-level events

**Problems:**
- ❌ No event **schema validation** — `payload` is `Dict[str, Any]`, no typed event schemas
- ❌ No event **replay** capability — cannot re-derive state from event log
- ❌ No **correlation_id** to link related events across project lifecycle
- ❌ `EventManager` is workspace-scoped — no cross-project event timeline
- ⚠️  `datetime.datetime.utcnow()` deprecated (Python 3.12+)
- ⚠️  Events not indexed by type — `list_events()` has no `event_type` filter

**Refactor Priority:** Medium — good foundation, needs query capability.

---

### 3.5 Workflow Engine
**Score: 8.0 / 10**

**Strengths:**
- ✅ Topological sort via stdlib `graphlib` — no external deps
- ✅ Supports dict-format AND list-format YAML
- ✅ Transitive skip propagation (FAILED → downstream SKIPPED)
- ✅ Event emission at every stage transition (STARTED/COMPLETED/FAILED/SKIPPED)
- ✅ `runner` callback pattern — loose coupling with application layer
- ✅ 9 unit tests covering parse, order, cycle detection, async run

**Problems:**
- ❌ **Not actually used** by `AgentCoordinator` — coordinator still uses hardcoded sequential execution
- ❌ No **retry** support per stage (e.g., `max_retries: 3` in YAML)
- ❌ No **parallel execution** — `TopologicalSorter` supports it but engine runs sequentially
- ❌ No **timeout** per stage
- ⚠️  `workflow.yaml` is generated by LLM (ArchitectAgent) but then ignored at runtime
- ⚠️  No `WorkflowDefinition` vs `WorkflowExecution` separation

**Refactor Priority:** HIGH — engine exists but is not wired into actual execution.

---

### 3.6 Capability Registry
**Score: 6.5 / 10**

**Strengths:**
- ✅ In-memory registry with 10 pre-registered capabilities
- ✅ Tag-based filtering
- ✅ `CapabilityDescriptor` maps logical ID → agent_type + tool
- ✅ 13 unit tests, all pass

**Problems:**
- ❌ **Not actually used** by `AgentCoordinator` — coordinator calls agents directly by class
- ❌ No `resolve()` method — registry is read-only lookup, not a dispatch mechanism
- ❌ No dynamic capability selection — registry doesn't influence which agent runs
- ❌ `agent_type` is a string — not a reference to an actual `Agent` class or factory
- ⚠️  Skills registered but no connection between registry + actual MCP skill invocation
- ⚠️  No capability versioning

**Refactor Priority:** HIGH — registry exists but is decorative, not functional.

---

### 3.7 AgentCoordinator (God Object)
**Score: 2.5 / 10**

**This is the most critical technical debt in the repository.**

**Problems:**
- ❌ **882 lines** in a single file — violates Single Responsibility Principle
- ❌ Instantiates **8 agents** in `__init__` — no lazy loading, no registry lookup
- ❌ Contains: project init, build orchestration, playwright testing, self-healing, security scanning — **5+ separate responsibilities**
- ❌ Directly manages SQLite DB (`SessionLocal`, `BuildTask`, `TestRun`, `SecurityScan`) — Coordinator should not own persistence
- ❌ Has hardcoded phase names (`Phase1`...`Phase6`) — not driven by `workflow.yaml`
- ❌ LLM prompt strings embedded inline (50-100 word prompts scattered across 882 lines)
- ❌ JSON parsing / stripping logic repeated 6+ times (`clean_json.startswith("```json")`)
- ❌ `run_playwright_test()` opens local files (`open(template_path)`) — bypasses `Environment`
- ❌ `auto_repair()` reuses `pm_agent` as forensics agent — role confusion
- ❌ Sequence: PM → Architect → Designer → Coder → CSS → Backend → QA → Security is **hardcoded**, not data-driven

**Refactor Priority:** CRITICAL — must be broken into specialized components.

---

### 3.8 BaseAgent / Agent Layer
**Score: 3.5 / 10**

**Problems:**
- ❌ `base.py` line 2: `import google.generativeai as genai` — **FutureWarning: deprecated SDK**
- ❌ `BaseAgent` duplicates all `LLMClient` logic — two separate LLM abstraction paths exist
- ❌ Agents call LLM via `call_llm(prompt)` — no token counting, no cost tracking, no retry policy
- ❌ `_initialize_llm()` reads `os.getenv()` directly — not injected, not testable without env vars
- ❌ No `Agent` interface/ABC — all agents inherit `BaseAgent` concretely
- ❌ Persona/system prompts are hardcoded strings in `personas.py` — not configurable
- ❌ Agents have no awareness of `Environment`, `ArtifactManager`, or `EventManager`
- ⚠️  `PMAgent` is named `ProductManager` but handles forensics repair — dual role

**Refactor Priority:** CRITICAL — agents must be re-grounded on platform contracts.

---

### 3.9 LLM Router
**Score: 4.0 / 10**

**Problems:**
- ❌ `LLMClient` and `BaseAgent._initialize_llm()` are **two separate implementations** of the same logic — divergence risk
- ❌ `google-generativeai` package deprecated — should migrate to `google.genai`
- ❌ No `LLMRouter` — provider selection is `if/else` hardcoded to env var
- ❌ No model registry — `gemini-1.5-flash` hardcoded in `os.getenv("GEMINI_MODEL", "gemini-1.5-flash")`
- ❌ No cost tracking — no token counting, no budget enforcement
- ❌ `async/sync` fallback pattern is dangerous — silent failure mode
- ❌ No rate limiting, no retry with exponential backoff
- ⚠️  `system_instruction` passed at construction — cannot be changed per call

**Refactor Priority:** HIGH — two divergent paths must be unified; deprecated SDK must be replaced.

---

### 3.10 Skills / MCP Layer
**Score: 5.0 / 10**

**Strengths:**
- ✅ 5 MCP skill servers defined
- ✅ `SkillServer` + `@tool` decorator abstraction
- ✅ `po_toolkit` skills are actually invoked (from `main.py`)

**Problems:**
- ❌ `html_coder`, `css_expert`, `backend_generator` skills are **never called** — coordinator uses agents directly
- ❌ `qa_playwright` skill server bypasses `Environment` (uses raw `subprocess`, `open()`)
- ❌ No standard skill invocation contract — skills are called via `from skills.X.server import fn`
- ❌ `po_toolkit` imported directly in `main.py` — bypasses MCP transport, no skill isolation
- ❌ Skills have no access to `ArtifactManager` — cannot record their outputs
- ⚠️  `SkillServer.run()` mutates a **global** `_registered_tools` list — not thread-safe

**Refactor Priority:** HIGH — skills should be the primary capability dispatch mechanism.

---

### 3.11 FastAPI Application (main.py)
**Score: 4.0 / 10**

**Problems:**
- ❌ **679 lines** in a single file
- ❌ Contains: Auth routes, Project build routes, PO routes, Sprint routes, Story routes, Dev Task routes, Chat routes — **7+ domains**
- ❌ `sys.path.append()` at line 14 — brittle import hack
- ❌ `/api/health` checks Redis inline — hard dependency on Redis even in dev
- ❌ `AgentCoordinator` constructed per-request — no connection pooling, no DI container
- ❌ `import redis` inside route handler — lazy import abuse
- ❌ `CORS allow_origins=["*"]` — production security risk
- ⚠️  No API versioning (`/api/v1/`)
- ⚠️  Response models partially typed (some routes return raw dicts)

**Refactor Priority:** HIGH — must be decomposed into routers by domain.

---

### 3.12 Database / Persistence Layer
**Score: 5.5 / 10**

**Strengths:**
- ✅ 7 SQLAlchemy models with proper relationships
- ✅ Auth + JWT implemented correctly

**Problems:**
- ❌ 3 `.db` files in root (`test.db`, `test_coordinator.db`, `web_creator.db`) — state leaking into repo
- ❌ `BuildTask.phase` is a free string (`Phase1`...`Phase6`) — should be an Enum linked to workflow stages
- ❌ `Project.status` is a free string — no state machine enforcement
- ❌ No migration system (Alembic) — schema changes require manual `create_all()`
- ❌ `SessionLocal` opened directly in `AgentCoordinator` — coordinator owns DB transaction lifecycle
- ⚠️  `datetime.datetime.utcnow()` deprecated throughout

**Refactor Priority:** Medium — add Alembic, add state machine enforcement.

---

### 3.13 PO Dashboard (po_dashboard/App.tsx)
**Score: 4.5 / 10**

**Problems:**
- ❌ **1,818 lines** in a single component — God Component
- ❌ All state in one `App()` function — 40+ `useState` hooks
- ❌ No component decomposition — auth, dashboard, backlog, sprint, chat all in one file
- ❌ No state management library (Redux/Zustand/Jotai) — prop drilling at scale
- ❌ No error boundary components
- ❌ `alert()` used for error handling — not production-appropriate
- ⚠️  `App.tsx` is 92KB — will cause slow builds and poor DX

**Refactor Priority:** Medium — decompose into feature folders.

---

### 3.14 CI/CD Pipeline
**Score: 3.5 / 10**

**Problems:**
- ❌ CI pipeline **continuously fails** — Python tests require LLM API keys not available in CI
- ❌ Redis dependency in health check means integration tests fail without Redis
- ❌ No mock strategy for LLM in CI — tests call real LLM APIs
- ❌ No environment variable injection via GitHub Secrets
- ❌ No separate `test` / `lint` / `build` / `security-scan` stages
- ❌ `pip install -r requirements.txt` without pinned versions — non-deterministic builds
- ⚠️  `pytest-asyncio` installed separately but not in `requirements.txt`
- ⚠️  No code coverage reporting
- ⚠️  No linting step (flake8/ruff)

**Refactor Priority:** HIGH — CI is the quality gate; a broken CI is worse than no CI.

---

## 4. God Objects Summary

| File | Lines | Responsibilities | Score |
|------|-------|-----------------|-------|
| `coordinator.py` | 882 | Orchestration, DB, File I/O, QA, Security, Self-Healing | 2.5/10 |
| `main.py` | 679 | Auth, Build, PO, Sprint, Story, Chat, Health | 4.0/10 |
| `App.tsx` | 1818 | Login, Dashboard, Backlog, Sprint, Chat, State | 4.5/10 |

---

## 5. Missing Platform Abstractions

These are listed in the target architecture but not yet implemented:

| Abstraction | Status | Priority |
|-------------|--------|----------|
| `platform/core/state_machine/` | ❌ Missing | HIGH |
| `platform/core/governance/` | ❌ Missing | Medium |
| `platform/core/evaluation/` | ❌ Missing | Medium |
| `platform/core/cost/` | ❌ Missing | Low |
| `platform/core/observability/` | ❌ Missing | Medium |
| `platform/ecosystem/agents/` | ❌ Not separated | HIGH |
| `platform/ecosystem/llm_router/` | ❌ Not unified | HIGH |
| ADR Generation (ArchitectAgent) | ❌ Missing | Medium |
| Benchmark Suite (`benchmarks/`) | ❌ Missing | Low |
| Alembic DB Migrations | ❌ Missing | Medium |

---

## 6. Tight Coupling Map

```
AgentCoordinator ──tight──► SQLite (SessionLocal)
AgentCoordinator ──tight──► 8 Agent classes (direct instantiation)
AgentCoordinator ──tight──► open() filesystem calls
BaseAgent        ──tight──► google.generativeai (deprecated)
BaseAgent        ──tight──► openai SDK
main.py          ──tight──► po_toolkit skill functions (direct import)
main.py          ──tight──► AgentCoordinator (per-request construction)
qa_playwright    ──tight──► subprocess (bypasses Environment)
cli.py           ──tight──► sys.path manipulation
worker.py        ──tight──► SessionLocal (duplicate DB access)
```

---

## 7. Technical Debt Register

| # | Debt Item | Severity | Effort | Priority |
|---|-----------|----------|--------|----------|
| D-01 | `BaseAgent` uses deprecated `google.generativeai` | 🔴 Critical | Small | Now |
| D-02 | `AgentCoordinator` is 882-line God Object | 🔴 Critical | Large | Sprint 7 |
| D-03 | `WorkflowEngine` not connected to actual execution | 🔴 Critical | Medium | Sprint 7 |
| D-04 | `CapabilityRegistry` not used for dispatch | 🔴 Critical | Medium | Sprint 7 |
| D-05 | CI pipeline permanently broken | 🔴 Critical | Small | Now |
| D-06 | `LLMClient` and `BaseAgent` duplicated LLM logic | 🟠 High | Medium | Sprint 8 |
| D-07 | Skills not invoked through Registry | 🟠 High | Medium | Sprint 8 |
| D-08 | No `StateMachine` for project lifecycle | 🟠 High | Medium | Sprint 7 |
| D-09 | `main.py` is 679-line God Router | 🟠 High | Medium | Sprint 9 |
| D-10 | `qa_playwright` bypasses `Environment` | 🟠 High | Small | Sprint 8 |
| D-11 | No Alembic migrations | 🟡 Medium | Small | Sprint 9 |
| D-12 | `App.tsx` is 1818-line God Component | 🟡 Medium | Large | Sprint 10 |
| D-13 | 3 `.db` files committed to repo | 🟡 Medium | Tiny | Now |
| D-14 | `datetime.utcnow()` deprecated everywhere | 🟡 Medium | Small | Sprint 8 |
| D-15 | No pinned dependency versions | 🟡 Medium | Small | Sprint 9 |
| D-16 | `sys.path.append()` in cli.py | 🟡 Medium | Small | Sprint 9 |

---

## 8. Refactor Priorities (Ordered)

### Immediate (No Code — Process)

1. **Fix CI Pipeline** — Add GitHub Secrets for LLM keys, add `-k "not integration"` flag for unit tests, pin pytest-asyncio in requirements.txt
2. **Delete `.db` files from Git** — Add to `.gitignore`

### Sprint 7: State Machine + Coordinator Decomposition

3. **Implement `platform_core/core/state_machine/`** — `State`, `Transition`, `StateMachine` for project lifecycle (CREATED → PLANNING → ARCHITECTING → CODING → REVIEWING → TESTING → DONE/FAILED)
4. **Wire `WorkflowEngine` into `AgentCoordinator`** — Replace hardcoded Phase1..Phase6 with engine-driven execution reading `workflow.yaml`
5. **Wire `CapabilityRegistry.resolve()`** — Add dispatch method; coordinator calls `registry.resolve("frontend_generation")` not `CoderAgent()`

### Sprint 8: Agent Layer + LLM Unification

6. **Migrate `BaseAgent` to use `LLMClient`** — Delete `_initialize_llm()` from BaseAgent; inject `LLMClient`
7. **Replace deprecated `google.generativeai`** — Migrate to `google.genai` SDK in `LLMClient`
8. **Fix `qa_playwright` Environment compliance** — Replace `subprocess.run()` with `env.run_command()`
9. **Fix `datetime.utcnow()`** — Replace with `datetime.now(datetime.timezone.utc)`

### Sprint 9: Application Layer Decomposition

10. **Decompose `main.py`** — Split into `routers/auth.py`, `routers/projects.py`, `routers/po.py`, `routers/chat.py`
11. **Add Alembic migrations** — Initialize `alembic/` with proper `env.py`
12. **Fix `sys.path.append()`** — Use `pyproject.toml` + proper package structure

### Sprint 10: Frontend + Evaluation

13. **Decompose `App.tsx`** — Feature folders: `features/auth/`, `features/dashboard/`, `features/backlog/`, `features/sprint/`, `features/chat/`
14. **Implement `benchmarks/`** — 4 benchmark projects (landing_page, crm, ecommerce, blog) with scoring

---

## 9. Target Architecture (Post-Refactor)

```
platform_core/
  core/
    environment/       ✅ Complete
    artifacts/         ✅ Complete (needs interface extraction)
    decisions/         ✅ Complete (needs typed Enums)
    events/            ✅ Complete (needs query capability)
    workflow/          ✅ Complete (needs runtime wiring)
    registry/          ✅ Complete (needs dispatch method)
    state_machine/     ❌ TODO Sprint 7
    llm_router/        ❌ TODO Sprint 8
    governance/        ❌ TODO Sprint 11
    evaluation/        ❌ TODO Sprint 10
    cost/              ❌ Backlog
    observability/     ❌ Backlog

apps/
  web_creator/
    agents/
      base_agent.py    ← Inject LLMClient (not import genai)
      pm_agent.py      ← Single responsibility
      architect_agent.py
      designer_agent.py
      coder_agent.py
      css_agent.py
      backend_agent.py
      qa_agent.py
      security_agent.py
    routers/
      auth.py
      projects.py
      po.py
      chat.py
    coordinator/
      build_coordinator.py  ← Orchestration only, no DB
      po_coordinator.py     ← PO workflow only
    services/
      project_service.py    ← DB operations
      build_service.py      ← Build state management

  po_dashboard/
    src/
      features/
        auth/
        dashboard/
        backlog/
        sprint/
        chat/
      shared/
        api.ts
        types.ts
```

---

## 10. Scoring Summary

| Subsystem | Score | Status |
|-----------|-------|--------|
| Environment Layer | 7.5/10 | ✅ Good — compliance gap |
| Artifact System | 7.0/10 | ✅ Good — needs interface |
| Decision System | 6.5/10 | ⚠️ Functional — semantically thin |
| Event System | 7.0/10 | ✅ Good — needs query |
| Workflow Engine | 8.0/10 | ✅ Strong — NOT WIRED |
| Capability Registry | 6.5/10 | ⚠️ Exists — NOT USED |
| AgentCoordinator | 2.5/10 | ❌ God Object — critical debt |
| BaseAgent / Agents | 3.5/10 | ❌ Deprecated SDK + duplication |
| LLM Router | 4.0/10 | ❌ Two paths, no router |
| Skills / MCP | 5.0/10 | ⚠️ Defined but bypassed |
| FastAPI App | 4.0/10 | ❌ God Router |
| Database Layer | 5.5/10 | ⚠️ No migrations |
| PO Dashboard | 4.5/10 | ❌ God Component |
| CI/CD Pipeline | 3.5/10 | ❌ Permanently failing |
| **OVERALL** | **5.8/10** | ⚠️ Transitioning |

---

## 11. The Central Thesis

The platform's most fundamental problem can be stated as:

> **Platform primitives have been built but not enforced.**

`WorkflowEngine` exists. It is not used.  
`CapabilityRegistry` exists. It is not used for dispatch.  
`Environment` exists. Skills bypass it.  
`LLMClient` exists. `BaseAgent` duplicates it.  

The next phase of work is not about building more platform modules.  
It is about **enforcing the platform contracts that already exist**.

The `AgentCoordinator` must become a thin orchestration shell that:
1. Reads `workflow.yaml` → `WorkflowEngine`
2. Resolves capabilities → `CapabilityRegistry`
3. Writes outputs → `ArtifactManager`
4. Records rationale → `DecisionManager`
5. Emits progress → `EventManager`
6. Transitions state → `StateMachine`

And does **nothing else**.

---

*Generated by Architecture Audit — Phase 1 Complete*  
*Next: Phase 7 (State Machine) + Coordinator Decomposition*
