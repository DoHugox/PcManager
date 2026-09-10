@echo off
chcp 65001 >nul
:: ==============================================================================
:: VNServerSentinel - 1-Click Administrator Setup Script for Windows
:: Tự động cài đặt thư viện, cấu hình quyền Administrator và chạy ngầm cùng Windows
:: ==============================================================================

echo.
echo =====================================================================
echo    VNServerSentinel - HỆ THỐNG QUẢN TRỊ MÁY CHỦ VIỆT NAM (1-CLICK SETUP)
echo =====================================================================
echo.

:: 1. Kiểm tra quyền Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] BẠN CẦN CHẠY BẰNG QUYỀN ADMINISTRATOR!
    echo     Vui lòng click chuột phải vào file install.bat và chọn "Run as administrator".
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0"

:: 2. Kiểm tra nếu đã có file PcManager.exe độc lập (Không cần Python)
if exist "PcManager.exe" (
    echo [+] Đã tìm thấy file thực thi độc lập: PcManager.exe!
    echo [+] Máy tính KHÔNG CẦN cài đặt Python!
    goto check_config
)
if exist "dist\PcManager.exe" (
    echo [+] Di chuyển dist\PcManager.exe ra thư mục gốc...
    move "dist\PcManager.exe" "PcManager.exe" >nul 2>&1
    echo [+] Đã sẵn sàng chạy PcManager.exe không cần Python!
    goto check_config
)

:: Nếu chưa có file EXE, kiểm tra Python để chạy dạng script
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [X] Chưa tìm thấy PcManager.exe hoặc Python trên máy!
    echo     Cách 1: Tải file PcManager.exe từ GitHub Releases và đặt vào đây.
    echo     Cách 2: Cài đặt Python 3 (Nhớ tick "Add python.exe to PATH"):
    echo     https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [+] Đang cài đặt các thư viện phụ trợ qua Python...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pywin32

:check_config
:: 3. Kiểm tra file cấu hình .env
if not exist ".env" (
    echo [*] Chưa có file .env. Đang tạo từ .env.example...
    copy ".env.example" ".env"
    echo.
    echo [!] Vui lòng mở file .env và điền Token Telegram Bot + Chat ID của bạn!
    notepad ".env"
)

:: 4. Đăng ký Windows Task Scheduler (Tự chạy ngầm với Watchdog tự hồi sinh)
echo [+] Đang đăng ký tác vụ tự khởi động cùng Windows (SYSTEM Privileges + Watchdog)...
set TASK_NAME=VNServerSentinel
set VBS_PATH=%~dp0watchdog.vbs

:: Xóa task cũ nếu có
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Tạo task mới chạy khi máy vừa bật nguồn (ONSTART) với quyền cao nhất
schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe \"%VBS_PATH%\"" /sc onstart /ru "SYSTEM" /rl HIGHEST /f

if %errorLevel% equ 0 (
    echo [OK] Đã đăng ký thành công dịch vụ tự chạy ngầm cùng Windows!
    echo [+] Đang khởi chạy ứng dụng ngay bây giờ...
    schtasks /run /tn "%TASK_NAME%"
) else (
    echo [!] Tạo task bằng SYSTEM không thành công, thử tạo bằng tài khoản hiện tại...
    schtasks /create /tn "%TASK_NAME%" /tr "wscript.exe \"%VBS_PATH%\"" /sc onstart /rl HIGHEST /f
    schtasks /run /tn "%TASK_NAME%"
)

echo.
echo =====================================================================
echo   CÀI ĐẶT HOÀN TẤT THÀNH CÔNG!
echo   Mở ứng dụng Telegram trên điện thoại và gõ /start để kiểm tra kết nối!
echo =====================================================================
echo.
pause
