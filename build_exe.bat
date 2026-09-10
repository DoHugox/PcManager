@echo off
chcp 65001 >nul
title Build PcManager.exe Standalone
cd /d "%~dp0"

echo.
echo =====================================================================
echo    ĐANG ĐÓNG GÓI PCMANAGER THÀNH 1 FILE EXE DUY NHẤT (STANDALONE)
echo =====================================================================
echo.

echo [+] Đang cài đặt công cụ PyInstaller và dependencies...
python -m pip install --upgrade pip
python -m pip install pyinstaller pywin32 -r requirements.txt

echo.
echo [+] Đang biên dịch mã nguồn thành 1 file PcManager.exe độc lập...
pyinstaller --clean PcManager.spec

if exist "dist\PcManager.exe" (
    echo.
    echo =====================================================================
    echo   [OK] ĐÓNG GÓI THÀNH CÔNG RỰC RỠ!
    echo   File thực thi duy nhất được lưu tại:
    echo   ---^> dist\PcManager.exe
    echo.
    echo   Bây giờ trên máy tính ở Việt Nam, bạn KHÔNG CẦN cài Python nữa!
    echo   Chỉ cần copy file PcManager.exe kèm file .env là chạy ngay!
    echo =====================================================================
) else (
    echo.
    echo [X] Đóng gói thất bại. Vui lòng kiểm tra log lỗi bên trên.
)
pause
