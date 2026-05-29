# 🤖 Web AI Platform (Multi-Agent, Skills & PO Toolkits)

Nền tảng đa tác nhân (Multi-Agent System) tổng quát phục vụ phát triển phần mềm, đóng gói các năng lực của Agent thành các **MCP Skills** độc lập, tích hợp quản lý dự án Product Owner chuyên nghiệp, tự động sinh code Fullstack, kiểm thử Playwright tự động, rà quét bảo mật SAST và điều khiển thông qua **PO Dashboard** thời gian thực.

Dự án được thiết kế dưới dạng **Monorepo** với kiến trúc phân rã rõ ràng giữa lõi xử lý (Core Platform), các kỹ năng (MCP Skills) và các ứng dụng nghiệp vụ (Apps). Hệ thống đã được nâng cấp hỗ trợ **chạy động trên mọi nền tảng (Cross-platform)** (Windows, macOS, Linux, Docker, CI/CD) không phụ thuộc vào đường dẫn ổ đĩa cứng.

---

## 📁 Cấu trúc Thư mục Monorepo

```text
web-skill/
├── .github/                      # Tự động hóa CI/CD
│   └── workflows/
│       └── ci.yml                # GitHub Actions chạy pytest (Python 3.12) & build React
├── core/                         # Thư viện lõi & SDK đa tác nhân
│   ├── coordinator/              # AgentCoordinator điều phối tổng quát
│   │   └── base.py               # Định nghĩa lớp GenericCoordinator và AgentPersona cơ bản
│   ├── skill_sdk/                # SDK đóng gói MCP Skill Server dùng FastMCP
│   │   └── server.py             # SkillServer tích hợp decorator @tool
│   └── llm/                      # Client kết nối LLM (Gemini, DeepSeek)
│       └── client.py             # Client tích hợp Gemini SDK & OpenAI API (cho DeepSeek)
├── skills/                       # Các MCP Skill Server độc lập giao tiếp qua STDIO/HTTP
│   ├── html_coder/               # Skill sinh mã HTML5 ngữ nghĩa và gán ID kiểm thử
│   ├── css_expert/               # Skill thiết kế theme và CSS Grid/Flexbox responsive
│   ├── backend_generator/        # Skill tạo cơ sở dữ liệu và API Express/Mongoose
│   ├── qa_playwright/            # Skill chạy test UI tự động & chẩn đoán lỗi console
│   └── po_toolkit/               # Bộ skill dành riêng cho Product Owner (Story, Prioritize, Estimate)
├── agents/                       # Cấu hình hành vi các Agent
├── apps/                         # Thư mục chứa các ứng dụng nghiệp vụ
│   ├── web_creator/              # Backend FastAPI & Celery Worker hiện tại
│   │   ├── app/
│   │   │   ├── agents/           # Module điều phối Agent tích hợp
│   │   │   │   ├── coordinator.py# Điều phối quy trình build 6 Pha, DESIGN.md & Self-Healing
│   │   │   │   └── personas.py   # Định nghĩa chỉ thị hệ thống cho từng Agent (gồm PM thiết kế DESIGN.md)
│   │   │   ├── db/               # SQLAlchemy models lưu trữ thông tin hệ thống & PO
│   │   │   │   ├── auth.py       # Mã hóa bcrypt mật khẩu & quản lý token JWT
│   │   │   │   ├── database.py   # Cấu hình SQLite engine và session động
│   │   │   │   └── models.py     # Cấu trúc bảng CSDL (User & liên kết sở hữu Project)
│   │   │   ├── mcp/              # Tích hợp MCP Client
│   │   │   ├── main.py           # FastAPI REST API (Auth, Story CRUD, Chat, Projects List, Health Check)
│   │   │   └── worker.py         # Celery task chạy ngầm cho tiến trình build dài hạn
│   │   ├── cli.py                # CLI điều hành ứng dụng
│   │   └── Dockerfile            # Dockerfile nâng cấp hỗ trợ Python 3.12 (Base image: Noble)
│   └── po_dashboard/             # Frontend React + TypeScript + Tailwind CSS + Lucide + Recharts
│       ├── dist/                 # Bản build tĩnh phục vụ trực tiếp qua FastAPI trang chủ
│       ├── src/
│       │   ├── App.tsx           # Router, Auth, Control Center, Backlog, Sprint Board & PO Chat
│       │   └── index.css         # Visual design tokens & Glassmorphism styling
│       └── package.json
├── tests/                        # Bộ kiểm thử tự động
│   ├── unit/                     # Unit test mock LLM cho po_toolkit và llm_client
│   │   ├── test_po_toolkit.py
│   │   └── test_llm.py
│   └── integration/              # Integration test dùng FastAPI TestClient & SQLite
│       └── test_api.py
├── docs/                         # Tài liệu hướng dẫn phát triển
│   ├── CREATING_SKILLS.md        # Hướng dẫn tạo & đăng ký MCP Skill mới
│   └── BUILD_YOUR_OWN_APP.md     # Hướng dẫn xây dựng app kiểu CodeCrafters
├── DESIGN.md                     # Mã thiết kế token Visual Identity của hệ thống (Obsidian Rose Gold)
├── docker-compose.yml            # Khởi chạy toàn bộ hệ thống bằng một câu lệnh
├── requirements.txt              # Danh sách thư viện Python (Đã tối ưu hóa và bổ sung đầy đủ)
└── web_creator.db                # SQLite database lưu trữ cục bộ (Tự động bỏ qua trong Git)
```

---

## 🎨 Lõi Thiết Kế & Google Labs `DESIGN.md`

Dự án áp dụng chặt chẽ đặc tả **Google Labs `DESIGN.md`** để đồng bộ hóa mã thiết kế (design tokens) giữa con người và các Agent lập trình.

1. **DESIGN.md Hệ Thống**: Nằm tại thư mục gốc ([DESIGN.md](DESIGN.md)), chứa cấu trúc YAML front-matter khai báo mã màu HSL (Obsidian Dark Background, Rose Gold Accent, Cyber Cyan), kích thước bo góc, khoảng cách, và prose Markdown giải thích lý do thiết kế.
2. **Spec-Driven Design sinh mã**: Khi bạn tạo dự án mới, tác nhân `PMAgent` sẽ tự động viết một tệp `DESIGN.md` riêng cho dự án đó. Các tác nhân lập trình hạ nguồn (**Designer**, **Coder**, **CSS Architect**) sẽ đọc tệp này để áp dụng chính xác mã màu, kiểu chữ và CSS variables, giúp website sinh ra có giao diện chuẩn mỹ thuật, hoàn toàn tách biệt với code logic và CSS.

---

## 💻 Ứng Dụng Product Owner Dashboard (`apps/po_dashboard`)

Frontend `po_dashboard` được xây dựng bằng **React + Vite + TypeScript + Tailwind CSS** và được biên dịch tĩnh trực tiếp vào `apps/po_dashboard/dist/` để FastAPI phục vụ tĩnh tại trang chủ `/` (Single-Port Fullstack Deployment).

### Các Phân Hệ Chính:
* **Màn hình Xác thực JWT**: Cho phép Đăng ký / Đăng nhập với phân quyền hệ thống (`PO` hoặc `Admin`).
* **Control Center (Bảng Điều Khiển)**:
  * Trực quan hóa tiến trình build 6 Pha thời gian thực qua Celery socket/polling.
  * Tích hợp báo cáo kiểm thử Playwright (Console violations, passed/failed) và rà quét bảo mật SAST (Vulnerabilities count).
  * Hỗ trợ nút **Chạy Sửa lỗi Tự động (Forensics)** sử dụng cơ chế self-healing.
  * Xem trực tiếp ứng dụng được sinh ra (Live Preview) trong iframe hoặc tab mới.
* **Agile Backlog Manager**:
  * Tự động sinh User Stories từ mô tả dự án bằng AI.
  * Ước lượng độ phức tạp (Fibonacci Story Points) và sắp xếp độ ưu tiên (MoSCoW) tự động qua LLM.
  * Thêm, sửa, xóa, kéo thả trạng thái các câu chuyện người dùng.
* **Sprint Board**:
  * Tạo chu kỳ Sprint và gán câu chuyện người dùng.
  * Checklist các đầu việc kỹ thuật chi tiết (Dev Tasks) phân rã cho lập trình viên (Database, API, Frontend, QA).
  * Vẽ biểu đồ **Sprint Burndown Chart (SVG)** theo dõi điểm nỗ lực còn lại.
* **PO Chat Assistant**: Trò chuyện thời gian thực với Trợ lý Product Owner Agent để làm mịn yêu cầu, hỗ trợ viết tiêu chí nghiệm thu (Acceptance Criteria).

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

## 📚 Hướng Dẫn Phát Triển & Sử Dụng Khác
* Xem [docs/CREATING_SKILLS.md](docs/CREATING_SKILLS.md) để học cách xây dựng và đóng gói thêm các MCP Skill Server độc lập.
* Xem [docs/BUILD_YOUR_OWN_APP.md](docs/BUILD_YOUR_OWN_APP.md) để làm quen với các bước dựng dự án thực tế tự hành kiểu CodeCrafters.
