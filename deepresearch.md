# KẾT QUẢ NGHIÊN CỨU CHUYÊN SÂU (DEEP RESEARCH)
## Kiến Trúc Tự Trị & Giám Sát Máy Chủ Homelab Từ Xa

### 1. Kiến Trúc IPC Vượt Session 0 Isolation
- Windows Service Agent chạy ở **Session 0** đóng vai trò là `NamedPipeServerStream`, mở đường hầm dữ liệu bảo mật.
- Desktop Agent chạy ở **User Session** (Session 1) đóng vai trò là client kết nối vào Named Pipe.
- Khi phát hiện sự kiện xâm nhập/unlock tại chỗ, Desktop Agent truyền tín hiệu nhị phân siêu nhẹ qua Named Pipe xuống Service.
- Cơ chế này vừa vượt qua giới hạn **Session 0 Isolation** của Windows, vừa đảm bảo quyền can thiệp hệ thống toàn vẹn ở cấp độ SYSTEM.

### 2. Chuỗi Phản Ứng Tự Vệ & Cảnh Báo Out-Of-Band (OOB)
- **Cưỡng ép khóa máy vật lý**: Desktop Agent lập tức gọi API hệ thống `LockWorkStation()` (`user32.dll`) để vô hiệu hóa không gian làm việc trong vòng mili-giây; kẻ gian vừa di chuột hoặc bật màn hình sẽ bị tống xuất ngay ra ngoài màn hình khóa (Lock Screen).
- **Thu thập chứng cứ**: Chụp ảnh màn hình desktop + webcam (nếu có phần cứng), đóng gói Event Logs.
- **Truyền tin qua Telegram Bot**: Lấy cảm hứng từ các thiết kế mã nguồn mở như:
  - [`trpcc`](https://github.com/xzripper/trpcc)
  - [`PythonRAT`](https://github.com/DarkCoderSc/PythonRAT)
- **Bảo mật Telegram Bot**:
  - **Chat ID Whitelisting**: Mã hóa cứng ID của người quản trị, thả (drop) vô điều kiện mọi tin nhắn từ người lạ.
  - **Execution Sandbox**: Chỉ cho phép phân giải các lệnh định sẵn như `/lock`, `/status`, `/reboot` thay vì mở shell PowerShell động vô tội vạ để triệt tiêu bề mặt tấn công chuỗi cung ứng.

### 3. Nền Tảng Quản Trị & Điều Khiển Từ Xa Toàn Năng (RMM & Remote Control)
- **MeshCentral (Intel)**: [https://github.com/Ylianst/MeshCentral](https://github.com/Ylianst/MeshCentral)
  - Nền tảng quản trị từ xa qua trình duyệt web toàn diện nhất (File Transfer, Terminal, Task Manager).
  - **Tuyệt chiêu Intel AMT / vPro**: Nếu CPU Intel hỗ trợ vPro, MeshCentral thiết lập đường hầm Out-Of-Band với chip Management Engine (ME) trên bo mạch chủ. Cho phép truy cập KVM ở cấp phần cứng: Kể cả khi Windows bị màn hình xanh (BSOD), treo cứng hoặc đang trong BIOS, kỹ sư tại Đài Loan vẫn xem được màn hình và dùng bàn phím ảo để cứu hộ!
- **RustDesk (High-FPS GUI Remote Desktop)**: [https://github.com/rustdesk/rustdesk](https://github.com/rustdesk/rustdesk)
  - Thay thế mã nguồn mở hoàn hảo cho TeamViewer/AnyDesk, viết bằng Rust, độ trễ cực thấp.
  - Tự host Relay Server ([`rustdesk-server`](https://github.com/rustdesk/rustdesk-server)) tại Đài Loan để mã hóa đầu cuối và tránh bị nhà mạng bóp băng thông quốc tế.
  - Kết hợp: MeshAgent/Telegram Bot làm launcher kích hoạt RustDesk ngầm chỉ khi cần dùng GUI, giúp tiết kiệm RAM máy cũ.

### 4. Cơ Chế Tự Động Cập Nhật An Toàn (Secure Auto-Update & CI/CD)
- **Velopack**: [https://github.com/velopack/velopack](https://github.com/velopack/velopack)
  - Nền tảng Auto-update hiện đại bằng Rust + C#.
  - **Delta Patching**: Tạo gói cập nhật vi phân `.delta.nupkg` nén zstd siêu tốc chỉ vài chục KB, cực kỳ tối ưu khi cáp quang quốc tế VN gặp sự cố.
  - Cập nhật qua `Update.exe` độc lập, kiểm tra SHA256 checksum, tự rollback nếu crash-on-boot.
- **WinSW (Windows Service Wrapper)**: [https://github.com/winsw/winsw](https://github.com/winsw/winsw)
  - Biến ứng dụng thành Windows Service SYSTEM.
  - Cấu hình `<onfailure action="restart" delay="10 sec"/>` đóng vai trò như System Watchdog cấp độ OS, tự hồi sinh tiến trình trong 10 giây nếu bị crash.

### 5. Xử Lý Sập Nguồn, Downtime & Cấu Hình BIOS Tự Bật Nguồn Từ Xa
- **Rủi ro pin CMOS**: Máy cũ bị chai pin CMOS sẽ tự reset BIOS về mặc định "Power Off" mỗi khi mất điện.
- **Giải pháp WMI / CIM định kỳ**: Agent trong Windows định kỳ dùng WMI/CIM hoặc công cụ dòng lệnh của hãng (HP CMSL, Dell Command Configure, Lenovo WMI) để ép ghi lại cấu hình "Restore on AC Power Loss -> Power On" vào NVRAM của BIOS.
