# 🛡️ PcManager (VNServerSentinel)
> **Hệ thống Quản trị & Giám sát Tự trị Toàn diện cho Máy chủ Windows từ xa qua Telegram**

[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011%20%7C%20Server-blue.svg)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/python-3.8%2B-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

---

## 🌟 Tính Năng Nổi Bật

1. **Quản lý Port & Dynamic IP không qua bên thứ 3**:
   - Tự động phát hiện khi địa chỉ IP WAN công cộng thay đổi và báo ngay về Telegram.
   - Quản lý mở/đóng/đổi Port Router từ xa qua giao thức **UPnP/IGD** (`/port open 8080 8080 TCP`) kết hợp tự động cấu hình **Windows Defender Firewall**.
2. **Bảo mật vật lý & Phát hiện kẻ dùng máy**:
   - Bắt sự kiện mở khóa tại bàn (`WTSRegisterSessionNotification`), phân biệt giữa phiên ngồi trước màn hình (Console Session) và phiên Remote Desktop.
   - Tự động chụp ảnh Webcam kẻ ngồi trước máy + Chụp ảnh màn hình Desktop gửi về Telegram kèm nút `[ 🔒 Khóa máy ngay ]`.
3. **Giám sát Sập nguồn & Cúp điện**:
   - Quét Windows Event Log (Event ID 41, 6008) để báo cáo nguyên nhân sập nguồn đột ngột, tính toán thời gian mất điện (downtime).
   - Tự động củng cố thiết lập *"Restore on AC Power Loss ➔ Power On"* vào BIOS NVRAM định kỳ giúp máy tự bật lại khi có điện kể cả khi pin CMOS đã cạn.
4. **On-Demand Remote Desktop (Tối ưu cho máy Core i3 / RAM yếu)**:
   - Thay vì để RustDesk/AnyDesk chạy ngầm 24/7 ngốn 200MB–300MB RAM, hệ thống hỗ trợ lệnh `/rd on` (bật ngầm khi cần) và `/rd off` (tắt giải phóng RAM khi xong).
5. **Quản lý File & Thư mục với quyền Administrator**:
   - Duyệt thư mục `/files`, đọc log `/cat`, tải file về điện thoại `/download`, gửi file từ điện thoại lên máy chủ, chạy lệnh PowerShell/CMD với quyền Admin cao nhất (`/exec <PIN> <cmd>`).
6. **Cơ chế Sinh tồn & Auto-Update An toàn**:
   - Watchdog tự động hồi sinh ứng dụng trong vòng 10 giây nếu bị crash.
   - Tự động cập nhật phiên bản mới từ GitHub Release (`/update run`) với cơ chế **Safe-Rollback trong 60 giây** nếu phiên bản mới bị lỗi hoặc mất kết nối.

---

## 🚀 Cài Đặt Nhanh (1-Click Setup)

1. Tải về hoặc giải nén thư mục vào máy tính Windows (Khuyến nghị: `C:\PcManager`).
2. Sao chép file `.env.example` thành `.env` và điền:
   - `TELEGRAM_BOT_TOKEN`: Token lấy từ `@BotFather`.
   - `TELEGRAM_ADMIN_CHAT_ID`: ID tài khoản cá nhân lấy từ `@userinfobot`.
   - `ADMIN_PIN`: Mã PIN bảo mật 4 số.
3. Nhấp chuột phải vào file **`install.bat`** chọn **`Run as administrator`**.
4. Mở Telegram gõ `/menu` để bắt đầu quản trị máy chủ!

Xem hướng dẫn chi tiết từng bước tại file [HUONG_DAN_CAI_DAT.md](HUONG_DAN_CAI_DAT.md).
