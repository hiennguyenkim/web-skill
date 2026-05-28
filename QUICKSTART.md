# Hướng dẫn chạy nhanh (Quickstart) - Web Creator Skill

Đây là tài liệu chứa 2 lệnh chạy tự hành (YOLO mode) giúp bạn khởi tạo và xây dựng website tự động bằng 1 dòng lệnh duy nhất từ terminal (PowerShell hoặc Command Prompt).

---

## 🚀 2 Lệnh Chạy Tự Hành (YOLO Mode)

### Lệnh 1: Xây dựng website từ File Word (.docx)
Sử dụng khi bạn đã chuẩn bị sẵn tệp tài liệu Word chứa yêu cầu thiết kế.
```powershell
gemini --skip-trust --approval-mode=yolo -p "/web-creator build yeucau.docx"
```

### Lệnh 2: Xây dựng website từ Ý tưởng chữ
Sử dụng khi bạn muốn mô tả trực tiếp ý tưởng trang web bằng văn bản.
```powershell
gemini --skip-trust --approval-mode=yolo -p "/web-creator build SportShop web app"
```

---

## 🛠️ Các Lệnh Nâng Cấp Bổ Sung (GSD Redux Style)

Nếu bạn không muốn chạy cả quy trình tự hành mà muốn điều khiển từng phần (quét mã nguồn có sẵn, lập kế hoạch riêng, hoặc sửa lỗi), bạn có thể chạy các câu lệnh nâng cấp sau:

### 1. Quét cấu trúc và thiết kế code hiện tại (Map Codebase)
Phân tích toàn bộ mã nguồn cũ để tự động cập nhật chỉ số thiết kế và phông chữ vào `PROJECT.md` mà không ghi đè:
```powershell
gemini --skip-trust --approval-mode=yolo -p "/web-creator map-codebase"
```

### 2. Lập kế hoạch chi tiết cho một Phase (Plan Phase)
Bẻ nhỏ một Phase trong lộ trình thành danh sách các đầu việc siêu nhỏ (micro-tasks):
```powershell
gemini --skip-trust --approval-mode=yolo -p "/web-creator plan-phase Phase3"
```

### 3. Tự động chẩn đoán và tự sửa lỗi (Forensics)
Quét toàn bộ trang web để tìm lỗi CSS (màu xấu, lệch khung) hoặc lỗi JS console và tự động viết bản vá sửa lỗi:
```powershell
gemini --skip-trust --approval-mode=yolo -p "/web-creator forensics"
```

## 🧪 Kiểm thử tự động bằng Playwright (Automated Testing)
Trong Phase 5 của quy trình `/web-creator build`, kỹ năng sẽ tự động:
1. Tạo một file kiểm thử `verify-ui.js` từ mẫu `playwright-template.js`.
2. Kiểm tra xem thư viện Playwright đã cài chưa. Nếu chưa, nó tự chạy lệnh cài đặt không cần hỏi (`npm install playwright` và `npx playwright install chromium`).
3. Khởi chạy Chrome ẩn danh (headless browser), tải trang web của bạn lên, kiểm tra xem có bất kỳ lỗi JavaScript nào xuất hiện trên console không.
4. Chụp toàn bộ giao diện và lưu tệp ảnh chụp tại `assets/verification_screenshot.png`.
5. Đảm bảo giao diện 100% không có lỗi trước khi hoàn tất phiên làm việc.

---

## 🛠️ Giải thích chi tiết các tham số
- `-y` hoặc `--yolo`: Bật chế độ YOLO tự động đồng ý mọi yêu cầu chỉnh sửa tệp tin, cài đặt phông chữ, chạy script của tác nhân AI mà không hỏi ý kiến người dùng trên màn hình.
- `-p` hoặc `--prompt`: Chạy ở chế độ không tương tác (headless mode), tự thực hiện lệnh được chỉ định từ đầu đến cuối và đóng lại sau khi hoàn tất.
- `/web-creator build [concept]`: Lệnh chính của kỹ năng `web-creator` để khởi tạo cấu trúc, chọn theme, lập trình giao diện, sinh hình ảnh, tối ưu hóa responsive và SEO tự động.
