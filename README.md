# 🤖 Web AI Platform: AI Engineering Platform

## 🌟 Tầm nhìn (Vision)
Repository này **không phải** là một công cụ tạo website tự động (AI Website Generator) đơn thuần. 

Đây là một **Nền tảng Kỹ nghệ AI (AI Engineering Platform)**. Mục tiêu dài hạn là cung cấp một nền tảng tái sử dụng được, có khả năng điều phối các luồng làm việc kỹ nghệ phần mềm tự động (autonomous) và có sự giám sát của con người (human-supervised) thông qua hệ thống ra quyết định có cấu trúc, các năng lực có thể tái sử dụng và hệ sinh thái kỹ năng mở rộng.

Các ứng dụng cụ thể như trình tạo website (Web Creator), trình tạo ứng dụng di động (Mobile App Generator), trợ lý quản lý sản phẩm (Product Management Assistant) hay các công cụ phát triển phần mềm trong tương lai là các **Sản phẩm (Products)** được xây dựng trên nền tảng này.

---

## 🧠 Triết lý Cốt lõi (Core Philosophy)
Hầu hết các hệ thống kỹ nghệ AI hiện nay thất bại vì chúng tập trung tối ưu hóa việc *sinh mã nguồn (generating code)* thay vì xây dựng *hạ tầng kỹ nghệ (engineering infrastructure)*. Nền tảng này tuân theo một triết lý khác biệt:

* **Quyết định quan trọng hơn Thành phẩm (Decisions > Artifacts)**: Lưu trữ lý do ra quyết định, thông tin sử dụng và người đưa ra quyết định thay vì chỉ lưu file code đầu ra.
* **Năng lực quan trọng hơn Triển khai (Capabilities > Implementations)**: Tách biệt ý định (Intent) của Agent khỏi cách thực thi kỹ thuật của Skill.
* **Tính ổn định của Nền tảng quan trọng hơn Tốc độ ra tính năng (Platform Stability > Feature Velocity)**.
* **Quản trị của con người là yếu tố cốt lõi (Human Governance)**: Hỗ trợ cộng tác và phê duyệt giữa Người - AI (Human-in-the-loop).
* **Đánh giá là bắt buộc (Evaluation First)**: Mọi thay đổi, prompt, agent, skill hay model đều phải đo lường được.
* **Mọi hành động của AI phải giải thích và truy vết được (Explainable & Traceable)**.

---

## 🏛️ Kiến trúc Phân tầng (Architectural Layers)

Hệ thống được chia làm ba phân lớp lớn rõ rệt:

```mermaid
graph TD
    subgraph Layer3 [Layer 3 - Products (Sản phẩm)]
        WC[Web Creator CLI & API]
        DB[Product Owner Dashboard]
        Mob[Future Mobile App Gen]
    end

    subgraph Layer2 [Layer 2 - Ecosystem (Hệ sinh thái)]
        AG[Agents Persona & Routing]
        SK[MCP Skills Registry]
        CAP[frontend_generation, test_execution...]
    end

    subgraph Layer1 [Layer 1 - Platform (Nền tảng)]
        ENV[Environment Abstraction - Sandboxing]
        DEC[Decision & Artifact Store]
        WF[Workflow & State Machine]
        GOV[Governance & Human Approval]
        OBS[Observability & Cost Tracking]
    end

    Layer3 -->|API/Adapter| Layer2
    Layer2 -->|Abstractions| Layer1
```

### 1. Phân lớp 1 — Nền tảng (Platform)
Cung cấp các hạt nhân cơ bản dùng chung cho toàn bộ hệ sinh thái. Không chứa logic nghiệp vụ cụ thể hay logic tạo website:
* **Quản lý Thành phẩm (Artifact Store)**: Lưu trữ các bản ghi bất biến (PRD, Stories, Code, Logs, Screenshots).
* **Quản lý Quyết định (Decision Store)**: Nhật ký ghi nhận các quyết định (PRD Approved, Database Selected, Security Review Failed).
* **Trừu tượng hóa Môi trường (Environment Layer)**: Cô lập việc đọc/ghi file và thực thi lệnh qua sandbox bảo mật.
* **Điều phối & Trạng thái (Workflow Engine & State Machine)**: Chạy các DAG công việc, quản lý trạng thái chuyển đổi (retry, resume, rollback).
* **Quản trị, Đo lường & Giám sát (Governance, Evaluation, Observability & Cost Tracking)**.

### 2. Phân lớp 2 — Hệ sinh thái (Ecosystem)
Chứa các thành phần AI có thể tái sử dụng:
* **Tác nhân (Agents)**: Định nghĩa hành vi, vai trò hệ thống, giao tiếp và định tuyến LLM (Gemini, DeepSeek). Tác nhân không trực tiếp gọi hệ điều hành mà thông qua năng lực của Ecosystem.
* **Kỹ năng (Skills)**: Các MCP Skill Server độc lập thực thi tác vụ cụ thể (STDIO/HTTP).
* **Năng lực (Capabilities)**: Trừu tượng hóa ý định hành động (ví dụ: `frontend_generation` capability) để Agent gọi, Registry sẽ tự động chọn Skill phù hợp nhất để triển khai.

### 3. Phân lớp 3 — Sản phẩm (Products)
Các ứng dụng giao diện người dùng đầu cuối. Chúng không bao giờ liên kết chặt chẽ (tightly coupled) với phần lõi nền tảng mà kết nối qua API & Adapter:
* **Web Creator**: Backend FastAPI, Celery background worker và CLI.
* **Product Owner Dashboard**: Giao diện React quản lý Sprint, Backlog, kiểm thử, bảo mật và tương tác AI.

---

## 📁 Cấu trúc Thư mục Monorepo Hiện tại

Hệ thống được tổ chức dạng **Monorepo** ánh xạ trực tiếp các khái niệm kiến trúc trên:

```text
web-skill/
├── core/                         # LAYER 1 & 2 - PLATFORM CORE & SDK
│   ├── coordinator/              # Lớp điều phối Workflow & State Machine cơ bản
│   │   └── base.py               # GenericCoordinator và trừu tượng hóa AgentPersona
│   ├── skill_sdk/                # SDK đóng gói MCP Skill (Environment Abstraction)
│   │   └── server.py             # SkillServer dùng FastMCP tích hợp decorator @tool
│   └── llm/                      # Lớp kết nối, định tuyến và tối ưu hóa LLM
│       └── client.py             # Client kết nối Gemini SDK & OpenAI API (cho DeepSeek)
├── skills/                       # LAYER 2 - MCP SKILLS ECOSYSTEM (Thực thi tác vụ)
│   ├── html_coder/               # Tạo layout HTML5 ngữ nghĩa và gán test ID
│   ├── css_expert/               # Thiết kế CSS responsive (Flexbox/Grid) theo DESIGN.md
│   ├── backend_generator/        # Tạo database schema & REST API Express/Mongoose
│   ├── qa_playwright/            # Kiểm thử trình duyệt tự động & chẩn đoán console errors
│   └── po_toolkit/               # Bộ công cụ Product Owner (Story Generation, Estimate, Prioritize)
├── agents/                       # LAYER 2 - AGENT DEFINITIONS (Hành vi tác nhân)
├── apps/                         # LAYER 3 - PRODUCTS (Ứng dụng nghiệp vụ người dùng)
│   ├── web_creator/              # Sản phẩm "Web Creator" (Backend FastAPI & CLI)
│   │   ├── app/
│   │   │   ├── agents/           # Điều phối quy trình build 6 Pha, DESIGN.md & Self-Healing
│   │   │   ├── db/               # Lưu trữ CSDL SQLAlchemy (Chứa Decision & Artifact dữ liệu)
│   │   │   │   ├── auth.py       # Quản lý mã hóa mật khẩu bcrypt & xác thực token JWT
│   │   │   │   ├── database.py   # Kết nối SQLite tự động thích ứng đa nền tảng
│   │   │   │   └── models.py     # Cấu trúc bảng Project, BuildTask, TestRun, SecurityScan
│   │   │   ├── main.py           # FastAPI REST API (Auth, Story CRUD, Chat, Projects List)
│   │   │   └── worker.py         # Celery task chạy ngầm thực thi các build job dài hạn
│   │   ├── cli.py                # CLI điều hành trực tiếp từ console
│   │   └── Dockerfile            # Container hóa (Ubuntu Noble - Python 3.12 & Node 18)
│   └── po_dashboard/             # Sản phẩm "PO Dashboard" (Frontend React SPA)
│       ├── dist/                 # Bản build tĩnh phục vụ trực tiếp tại root API "/"
│       ├── src/
│       │   ├── App.tsx           # Control Center, Backlog, Kanban Sprint Board, Burndown & Chat
│       │   └── index.css         # Glassmorphism styling & visual design tokens
│       └── package.json
├── tests/                        # EVALUATION SYSTEM (Hệ thống đánh giá chất lượng)
│   ├── unit/                     # Unit test mock LLM offline cho po_toolkit và llm_client
│   │   ├── test_po_toolkit.py
│   │   └── test_llm.py
│   └── integration/              # Integration test API đầy đủ thông qua SQLite test tạm thời
│       └── test_api.py
├── docs/                         # Tài liệu hướng dẫn phát triển nền tảng
│   ├── CREATING_SKILLS.md        # Hướng dẫn tạo & tích hợp thêm MCP Skill mới vào hệ sinh thái
│   └── BUILD_YOUR_OWN_APP.md     # Hướng dẫn cách tự xây dựng một ứng dụng sản phẩm mới
├── .github/                      # CI/CD PIPELINE (Tự động chạy kiểm thử trên GitHub Actions)
│   └── workflows/
│       └── ci.yml                # Setup Python 3.12 & Node 18, chạy pytest & build React frontend
├── DESIGN.md                     # Mã thiết kế token Visual Identity của hệ thống (Obsidian Rose Gold)
├── docker-compose.yml            # Khởi chạy toàn bộ nền tảng chỉ bằng 1 câu lệnh
└── requirements.txt              # Thư viện Python yêu cầu (Tối ưu hóa đa nền tảng)
```

---

## 🎨 Lõi Thiết Kế & Google Labs `DESIGN.md`

Nền tảng áp dụng đặc tả **Google Labs `DESIGN.md`** để đồng bộ hóa các quyết định thiết kế trực quan (design tokens) giữa con người và AI.

1. **DESIGN.md Hệ Thống**: Nằm tại thư mục gốc ([DESIGN.md](DESIGN.md)), chứa cấu trúc YAML front-matter khai báo mã màu HSL (Obsidian Dark Background, Rose Gold Accent, Cyber Cyan), kích thước bo góc, khoảng cách, và prose Markdown giải thích lý do thiết kế.
2. **Spec-Driven Design**: Khi bạn tạo dự án mới, tác nhân `PMAgent` sẽ tự động viết một tệp `DESIGN.md` riêng cho dự án đó. Các tác nhân lập trình hạ nguồn (**Designer**, **Coder**, **CSS Architect**) sẽ đọc tệp này để áp dụng chính xác mã màu, kiểu chữ và CSS variables, giúp website sinh ra có giao diện chuẩn mỹ thuật, hoàn toàn tách biệt với code logic và CSS.

---

## 🔐 Bảo Mật & Xác Thực (JWT & Bcrypt)

Toàn bộ hệ thống API được bảo vệ bằng lớp middleware bảo mật:
* **Hashed Password**: Mật khẩu người dùng được băm bằng thuật toán `bcrypt` trước khi lưu trữ vào SQLite.
* **JWT Authorization**: Đăng nhập trả về mã thông báo JWT có chữ ký thuật toán `HS256` và hết hạn sau 24 giờ.
* Các API quản trị dự án (`/api/project/...`) và quản trị PO (`/api/po/...`) yêu cầu Header: `Authorization: Bearer <JWT_TOKEN>`.
* Cấp quyền sở hữu dự án: PO chỉ được xem và thao tác trên dự án do chính mình tạo ra. Admin có toàn quyền quản trị toàn bộ hệ thống.

---

## 🧪 Hệ Thống Kiểm Thử Tự Động (`tests/`)

Dự án tích hợp bộ test suite đầy đủ cho cả Unit test và Integration test chạy qua `pytest`:

1. **Unit Tests (MCP Skills & LLM Client)**:
   * [test_po_toolkit.py](tests/unit/test_po_toolkit.py): Kiểm thử 4 công cụ của PO Toolkit bằng cách giả lập (mock) phản hồi từ LLMClient, chạy độc lập offline không tốn phí API.
   * [test_llm.py](tests/unit/test_llm.py): Kiểm thử khả năng khởi tạo cấu hình Gemini/DeepSeek và cơ chế tự động fallback từ cuộc gọi `async` sang `sync` khi lỗi.
2. **Integration Tests (API Endpoints)**:
   * [test_api.py](tests/integration/test_api.py): Khởi động FastAPI `TestClient` kết nối tới database SQLite test tạm thời, kiểm thử toàn trình đăng ký, đăng nhập JWT, truy vấn thông tin người dùng và khởi tạo dự án.

Chạy bộ test suite bằng dòng lệnh:
```bash
python -m pytest -v tests/
```

---

## 🔁 Tích Hợp CI/CD (GitHub Actions)

Tệp tin cấu hình pipeline nằm tại [.github/workflows/ci.yml](.github/workflows/ci.yml). Khi có sự kiện `push` hoặc `pull_request` vào nhánh `main` hoặc `master`:
1. Khởi chạy môi trường máy ảo Ubuntu, cài đặt **Python 3.12** và **Node.js 18**.
2. Cài đặt các gói thư viện Python và chạy bộ test suite `pytest`.
3. Cài đặt các thư viện Node.js và chạy lệnh `npm run build` để kiểm tra độ tin cậy khi đóng gói Frontend Dashboard.

---

## ⚡ Hướng Dẫn Khởi Chạy & Sử Dụng

### Yêu cầu hệ thống:
* **Python 3.12+** (bắt buộc vì thư viện phân tích bảo mật `strix-agent` yêu cầu Python 3.12+)
* **Node.js 18+**
* **Redis** (dành cho Celery Broker)

### 1. Thiết lập môi trường
Tạo file `.env` từ file `.env.example` và điền đầy đủ thông tin API Key (Gemini hoặc DeepSeek). Cài đặt các thư viện:
```bash
# Cài đặt thư viện Python
pip install -r requirements.txt

# Cài đặt trình duyệt chạy Playwright UI
npx playwright install chromium
```

### 2. Khởi chạy Hệ Thống REST API & Worker cục bộ
Mở 3 cửa sổ terminal riêng biệt để chạy các dịch vụ:

* **Tab 1: Khởi động Redis** (Broker cho Celery).
* **Tab 2: Khởi động FastAPI HTTP Server**:
  ```bash
  python cli.py serve --port 8000
  ```
  Truy cập Dashboard trực tiếp tại: `http://localhost:8000/`
  Swagger API Docs tương tác: `http://localhost:8000/docs`

* **Tab 3: Khởi động Celery Worker**:
  ```bash
  python cli.py worker
  ```

### 3. Khởi chạy bằng Docker Compose (Khuyên dùng)
Bạn có thể khởi chạy toàn bộ môi trường (Redis, FastAPI Server, Celery Worker) bằng một câu lệnh duy nhất:
```bash
docker-compose up --build
```
Hệ thống sẽ tự động cấu hình cơ sở dữ liệu động và đồng bộ mã nguồn trực tiếp.

---

## 🗺️ Lộ trình Phát triển Nền tảng (Platform Roadmap)

* **Phase A (Hiện tại - Đã hoàn thành)**: Xây dựng cấu trúc Artifact Store, Decision Store lưu trữ SQLite, Trừu tượng hóa môi trường (Skill SDK).
* **Phase B (Hiện tại - Đã hoàn thành)**: Thiết lập Workflow Engine (6 Pha tích hợp), State Machine (persist SQLite) và Governance (PO duyệt thủ công).
* **Phase C (Tiếp theo)**: Xây dựng Capability Registry, Skill Registry, Capability Graph để tự động định tuyến nhiệm vụ từ Agent qua registry thay vì chỉ định skill trực tiếp.
* **Phase D**: Nâng cấp hệ thống Agents, Bộ nhớ ngữ cảnh (Memory) và hệ tri thức validated decisions (Knowledge).
* **Phase E**: Phát triển hệ thống Evaluation chất lượng code tự động, Cost Tracking tài nguyên sử dụng và Observability truy vết chi tiết quyết định của Agent.
* **Future**: Thiết lập Marketplace cho các nhà phát triển tạo Skills mới, Multi-tenant Platform chạy phân tán.

---

## 📜 Nguyên tắc Quyết định Cuối cùng (Final Principle)

Trước khi thêm bất kỳ tính năng mới nào vào repository này, hãy tự trả lời một câu hỏi duy nhất:

> **Tính năng này sẽ củng cố Nền tảng (Platform), mở rộng Hệ sinh thái (Ecosystem), hay tạo ra một Sản phẩm (Product)?**

Nếu câu trả lời không thuộc bất kỳ điều nào ở trên, tính năng đó **không thuộc về** repository này. Mục tiêu không phải là tạo ra nhiều tác nhân riêng lẻ, mà là xây dựng một nền tảng kỹ nghệ AI bền vững có khả năng hỗ trợ bất kỳ sản phẩm kỹ nghệ tự trị nào trong tương lai.
