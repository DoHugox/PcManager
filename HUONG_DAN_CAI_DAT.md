# 📘 HƯỚNG DẪN CÀI ĐẶT & SỬ DỤNG VNSERVERSENTINEL

> **Dành cho bạn**: Bạn đang ở Đài Loan quản lý máy chủ Windows (PC cũ) đặt tại nhà ở Việt Nam.
> Mọi thao tác cài đặt chỉ cần làm **1 lần duy nhất** qua AnyDesk/Ultraviewer, sau đó bạn có thể quản lý 100% qua Telegram.

---

## BƯỚC 1: CHUẨN BỊ (Làm trên điện thoại tại Đài Loan - 2 phút)

### 1. Tạo Bot Telegram của riêng bạn
1. Mở Telegram, tìm kiếm bot tên là **`@BotFather`** (có dấu tích xanh).
2. Nhắn tin: `/newbot`
3. Đặt tên hiển thị cho bot (Ví dụ: `May Chu VN Sentinel`).
4. Đặt username cho bot (Phải kết thúc bằng chữ `bot`, ví dụ: `my_vn_server_sentinel_bot`).
5. BotFather sẽ gửi cho bạn một đoạn **Token** (dạng: `7123456789:AAFx...`). 👉 **Hãy copy lưu lại Token này**.

### 2. Lấy Chat ID của bạn (Để bảo mật, chỉ bạn mới điều khiển được)
1. Trên Telegram, tìm bot tên là **`@userinfobot`**.
2. Nhấn `/start`, bot sẽ trả về thông tin của bạn.
3. Tìm dòng **`Id:`** (dạng số nguyên, ví dụ: `123456789`). 👉 **Hãy copy lưu lại số ID này**.

### 3. (Tùy chọn) Tạo Dead-Man's Switch báo mất điện
1. Truy cập [Healthchecks.io](https://healthchecks.io) (hoàn toàn miễn phí).
2. Tạo 1 check mới, chọn chu kỳ `Period: 2 minutes`, `Grace time: 2 minutes`.
3. Tích hợp gửi thông báo về Telegram của bạn.
4. Copy đường link Ping (dạng: `https://hc-ping.com/xxxx-xxxx...`).
*(Khi nhà ở VN cúp điện, sau 2 phút Healthchecks không nhận được ping từ máy tính sẽ tự động gửi tin nhắn báo bạn ngay lập tức!)*

---

## BƯỚC 2: CÀI ĐẶT LÊN MÁY TÍNH Ở VIỆT NAM (Qua AnyDesk / Ultraviewer)

1. Đưa toàn bộ thư mục **`VNServerSentinel`** vào máy tính ở Việt Nam (Khuyến nghị đặt tại: `C:\VNServerSentinel`).
2. Mở file **`.env`** (hoặc đổi tên `.env.example` thành `.env`) bằng Notepad và điền:
   ```ini
   TELEGRAM_BOT_TOKEN=điền_token_của_bạn_vào_đây
   TELEGRAM_ADMIN_CHAT_ID=điền_chat_id_của_bạn_vào_đây
   ADMIN_PIN=1234
   HEARTBEAT_URL=link_healthchecks_nếu_có
   ```
3. **Cài đặt 1-Click tự động**:
   - Nhấp chuột phải vào file **`install.bat`** ➔ Chọn **`Run as administrator`**.
   - Script sẽ tự động:
     - Tải và cài đặt các thư viện cần thiết (`requests`, `psutil`, `opencv`, `Pillow`, `upnpy`, `pywin32`).
     - Đăng ký dịch vụ chạy ngầm vào **Windows Task Scheduler** với quyền **SYSTEM Administrator cao nhất** (Máy vừa bật lên là tự chạy ngầm trước khi người dùng đăng nhập).
     - Khởi động ứng dụng ngay lập tức.
4. Kiểm tra điện thoại: Bot Telegram của bạn sẽ gửi tin nhắn:
   > 🟢 **MÁY CHỦ VIỆT NAM ĐÃ TRỰC TUYẾN!** kèm địa chỉ IP WAN và Local IP.

---

## BƯỚC 3: CẤU HÌNH BIOS TỰ BẬT MÁY KHI CÓ ĐIỆN LẠI (TỪ XA)

Vì bạn ở xa không thể vào BIOS thủ công:
1. Trên máy ở VN, mở PowerShell bằng quyền Administrator.
2. Chạy file script có sẵn:
   ```powershell
   powershell -ExecutionPolicy Bypass -File C:\VNServerSentinel\bios_helper.ps1
   ```
*(Script sẽ tự phát hiện máy Dell, HP, Lenovo và kích hoạt chế độ "Power On after AC Loss" ngay trong Windows).*

---

## BƯỚC 4: BẢNG TRA CỨU CÁC LỆNH ĐIỀU KHIỂN TRÊN TELEGRAM

Bạn chỉ cần nhắn tin cho Bot Telegram:

| Lệnh | Ý nghĩa & Cách dùng |
| :--- | :--- |
| `/menu` hoặc `/start` | Mở bảng điều khiển với các nút bấm nhanh trực quan |
| `/status` | Xem chi tiết: CPU, RAM, Ổ cứng C/D, Uptime, IP, ai đang đăng nhập |
| `/ip` | Xem Public WAN IP hiện tại và Local LAN IP |
| `/screen` | Chụp ngay ảnh màn hình Desktop gửi về điện thoại |
| `/cam` | Bật Webcam chụp ảnh ai đang ngồi trước máy tính |
| `/lock` | Khóa màn hình Windows ngay lập tức |
| `/port list` | Xem các cổng (port) đang được mở trên Router Wi-Fi qua UPnP |
| `/port open <ext> <int> [TCP/UDP]` | **Mở port Router từ xa**. Ví dụ: `/port open 8080 8080 TCP` (Tự động mở port trên modem và tạo rule trên Windows Firewall) |
| `/port close <ext> [TCP/UDP]` | Đóng port đã mở trên modem. Ví dụ: `/port close 8080 TCP` |
| `/rd on` | **Bật Remote Desktop (RustDesk) ngầm** khi bạn cần kết nối điều khiển màn hình từ Đài Loan |
| `/rd off` | **Tắt Remote Desktop** khi dùng xong để giải phóng ~200MB RAM & CPU cho chip Core i3 |
| `/rd status` | Kiểm tra xem RustDesk có đang chạy hay không |
| `/files` hoặc `/dir [đường_dẫn]` | Duyệt danh sách tệp & thư mục (Ví dụ: `/files C:\`) |
| `/cat <đường_dẫn_file>` | Đọc nội dung file text/log trực tiếp trên Telegram |
| `/download <đường_dẫn_file>` | Tải file từ máy tính về điện thoại (Ví dụ: `/download C:\backup\db.zip`) |
| **Gửi bất kỳ file nào vào Telegram** | Bot sẽ tự động tải file đó và lưu vào máy tính ở Việt Nam |
| `/mkdir <thư_mục>` | Tạo thư mục mới trên máy chủ |
| `/rm <mã_PIN> <đường_dẫn>` | Xóa an toàn tệp/thư mục (Ví dụ: `/rm 1234 C:\temp\test.txt`) |
| `/exec <mã_PIN> <lệnh>` | **Chạy lệnh PowerShell/CMD với quyền Administrator cao nhất** (Ví dụ: `/exec 1234 Get-Service`, `/exec 1234 Restart-Service wuauserv`) |
| `/reboot <mã_PIN>` | Khởi động lại máy tính an toàn (`/reboot 1234`) |
| `/shutdown <mã_PIN>` | Tắt máy tính (`/shutdown 1234`) |
| `/update check` | Kiểm tra xem trên GitHub có bản cập nhật mới hay không |
| `/update run` | **Tự động nâng cấp phiên bản mới từ xa** (Kèm cơ chế Safe-Rollback an toàn trong 60s) |

---

## BƯỚC 5: CÁC TÍNH NĂNG TỰ ĐỘNG THÔNG MINH

1. **Khi nhà mạng tại VN đổi IP**:
   - Hệ thống tự động phát hiện và gửi tin nhắn cảnh báo IP mới kèm đường link truy cập ngay cho bạn.
2. **Khi nhà ở VN bị cúp điện rồi có điện lại**:
   - Máy tính tự bật nguồn ➔ VNServerSentinel khởi động ➔ Kiểm tra nhật ký Windows Event 41/6008 ➔ Báo cáo:
     > ⚠️ **MÁY CHỦ VIỆT NAM VỪA KHỞI ĐỘNG LẠI!**
     > - Thời gian mất điện: 25 phút
     > - Nguyên nhân: Sập nguồn đột ngột (Cúp điện)
     > - IP mạng mới: `14.241.xx.xx`
3. **Khi có ai đó ở nhà mở máy tính hoặc cắm chuột sử dụng**:
   - Hệ thống phát hiện sự kiện mở khóa tại chỗ (Physical Unlock) ➔ Tự động bật Webcam chụp khuôn mặt + Chụp màn hình Desktop ➔ Bắn ngay vào Telegram của bạn kèm nút `[ 🔒 Khóa máy ngay lập tức ]`.
4. **Cơ chế Safe Auto-Update**:
   - Khi cập nhật phiên bản mới, hệ thống kích hoạt bộ đếm thời gian 60 giây. Nếu bản mới bị crash hoặc mất kết nối mạng, hệ thống **tự động hoàn tác (rollback) về bản cũ** để bạn không bao giờ mất quyền điều khiển máy chủ.
5. **Watchdog tự hồi sinh sau 10 giây (Tương tự WinSW)**:
   - Được tích hợp sẵn vòng lặp Watchdog ngầm. Nếu tiến trình bị crash hoặc bị ai đó vô tình tắt, hệ thống sẽ tự động khởi động lại sau 10 giây.
6. **Tự củng cố BIOS chống chai pin CMOS**:
   - Mỗi ngày một lần, hệ thống tự động ghi đè thiết lập "Có điện tự bật máy" vào NVRAM của bo mạch chủ, giúp máy vẫn tự bật khi có điện kể cả khi pin CMOS trên chiếc PC cũ đã cạn.
