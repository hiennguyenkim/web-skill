# ⚡ Quickstart - Web Creator Skill

Tài liệu hướng dẫn nhanh các lệnh chạy tự hành (YOLO mode) để khởi tạo và xây dựng website tự động bằng 1 dòng lệnh duy nhất.

---

## 🚀 Lệnh Xây Dựng Tự Hành (YOLO Mode)

Chạy trực tiếp từ PowerShell/Cmd tại thư mục dự án của bạn:

```powershell
# 1. Từ file Word (.docx) chứa yêu cầu
gemini --skip-trust --approval-mode=yolo -p "/web-creator build yeucau.docx"

# 2. Từ ý tưởng chữ mô tả trực tiếp
gemini --skip-trust --approval-mode=yolo -p "/web-creator build SportShop web app"
```

---

## 🛠️ Lệnh Nâng Cao Bổ Sung (GSD Style)

```powershell
# Quét cấu trúc và phông chữ của dự án hiện tại (không ghi đè)
gemini --skip-trust --approval-mode=yolo -p "/web-creator map-codebase"

# Lập lộ trình chi tiết cho một Phase cụ thể
gemini --skip-trust --approval-mode=yolo -p "/web-creator plan-phase Phase3"

# Tự động quét lỗi CSS/Console và tự động sửa chữa bằng bản vá
gemini --skip-trust --approval-mode=yolo -p "/web-creator forensics"
```

---

## 🧪 Kiểm Thử Tự Động & Chẩn Đoán (Playwright)

Quy trình `/web-creator build` (Phase 5) sẽ tự động kích hoạt:
1. Tạo kịch bản kiểm thử `verify-ui.js` từ `playwright-template.js`.
2. Kiểm tra/Tự cài đặt thư viện `playwright` và `chromium` headlessly.
3. Chạy kiểm thử trên Desktop & Mobile để phát hiện lỗi console hoặc vỡ khung (layout overflow).
4. Xuất kết quả báo cáo trực quan dạng kính mờ tại `assets/test_report.html` và ảnh chụp màn hình.

---

## ⚙️ Giải Thích Tham Số
- `--skip-trust`: Bỏ qua các câu hỏi xác thực thư mục tin cậy của hệ thống.
- `--approval-mode=yolo`: Tự động đồng ý mọi yêu cầu chỉnh sửa/chạy tập lệnh của AI.
- `-p "[lệnh]"`: Chạy lệnh chỉ định ở chế độ không tương tác (headless) và đóng khi hoàn tất.
