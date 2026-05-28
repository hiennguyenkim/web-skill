# 🤖 Web Creator Multi-Agent Platform

Nền tảng tự động thiết kế, lập trình và kiểm thử giao diện website bằng hệ thống đa tác nhân (Multi-Agent) thông minh kết hợp cơ chế tự động chẩn đoán lỗi trong môi trường sandbox.

Dự án được xây dựng dựa trên ý tưởng từ các nền tảng tác nhân hàng đầu thế giới:
- **MetaGPT & crewAI**: Phân vai và phân chia luồng bàn giao (Handoff Protocols) giữa Product Manager, UI/UX Designer, Frontend Coder, CSS Architect và QA Engineer.
- **Playwright & OpenHands / AutomationTest**: Tự động hóa kiểm thử đa màn hình (Responsive testing), chẩn đoán lỗi JavaScript console và kích hoạt vòng lặp tự sửa lỗi (Self-healing loop) bằng bản vá thông qua LLM.

---

## 📁 Cấu trúc Thư mục

```text
d:/ai-web-skill/
├── app/
│   ├── agents/          # Điều phối đa tác nhân (PM, Designer, Coder, CSS, QA)
│   ├── db/              # Cơ sở dữ liệu SQLite & SQLAlchemy schema
│   ├── mcp/             # Cấu hình Model Context Protocol (FastMCP)
│   └── main.py          # FastAPI HTTP Server endpoints
├── .gemini/             # Skill định cấu hình cho Gemini CLI
├── .claude/             # Skill định cấu hình cho Claude Code
├── cli.py               # Công cụ tương tác dòng lệnh (CLI tool)
├── Dockerfile           # Đóng gói môi trường ảo (Playwright base image)
├── QUICKSTART.md        # Hướng dẫn nhanh về các lệnh YOLO
└── README.md            # Tài liệu dự án
```

---

## 🚀 Cài đặt Nhanh (Local Setup)

### 1. Chuẩn bị Môi trường
Yêu cầu hệ thống đã cài đặt **Python 3.10+** và **Node.js** (để chạy Playwright).

```bash
# Cài đặt các phụ thuộc Python
pip install -r requirements.txt

# Cài đặt trình duyệt ẩn cho Playwright
npx playwright install chromium
```

### 2. Cấu hình Khóa API
Sao chép tệp `.env.example` thành `.env` và nhập khóa API Gemini của bạn:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```

---

## 💻 Hướng dẫn Sử dụng

### 1. Dựng Web Trực Tiếp qua dòng lệnh (CLI Build)
Khởi tạo và biên dịch tự động giao diện trực tiếp từ Terminal:
```bash
python cli.py build "BeautyStore" "Một trang bán mỹ phẩm phong cách obsidian rose gold sang trọng"
```

### 2. Khởi chạy FastAPI Web Server
Chạy máy chủ HTTP để điều khiển từ xa hoặc tích hợp frontend bên thứ ba:
```bash
python cli.py serve --port 8000
```
- Truy cập tài liệu tương tác Swagger API tại: `http://localhost:8000/docs`
- API hỗ trợ các cổng: `/api/project/init`, `/api/project/build/{id}`, `/api/project/{id}/status`, và `/api/project/forensics/{id}`.

### 3. Khởi chạy Celery Background Worker
Đảm bảo bạn đã khởi chạy dịch vụ **Redis** trên máy local (mặc định tại `redis://localhost:6379/0`), sau đó khởi chạy Celery worker:
```bash
python cli.py worker
```

### 4. Khởi chạy máy chủ MCP (Model Context Protocol)
Chia sẻ các công cụ của Web Creator tới các AI Client hỗ trợ MCP (như Claude Desktop, Cursor, v.v.) qua giao tiếp STDIO:
```bash
python cli.py mcp
```

---

## 🐳 Sử dụng với Docker

Đóng gói và chạy dịch vụ cách ly trong container (đã tích hợp sẵn trình duyệt không đầu của Playwright):

```bash
# Xây dựng Docker Image
docker build -t web-creator-platform .

# Chạy Web Server bằng Docker
docker run -p 8000:8000 --env-file .env web-creator-platform

# Chạy Celery Background Worker bằng Docker
docker run --env-file .env web-creator-platform python3 cli.py worker
```

---

## 🛡️ Giấy phép & Đóng góp
Dự án được phân phối dưới dạng nguồn mở. Vui lòng tham khảo các tệp tin trong `.gemini/` và `.claude/` để cấu hình tích hợp thêm cho các IDE/CLI tương ứng.
