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
    echo   [OK] ĐÃ TẠO FILE THỰC THI: dist\PcManager.exe (CÓ ICON)
    echo =====================================================================
    
    :: Kiểm tra nếu máy có Inno Setup để tạo file Setup Wizard
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        echo.
        echo [+] Đang tạo bộ cài đặt chuyên nghiệp PcManager_Setup.exe...
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
        if exist "dist\PcManager_Setup.exe" (
            echo   [OK] ĐÃ TẠO BỘ CÀI ĐẶT CHUẨN WINDOWS: dist\PcManager_Setup.exe
        )
    )
    echo.
    echo   Tất cả file sẵn sàng trong thư mục "dist\".
    echo =====================================================================
) else (
    echo.
    echo [X] Đóng gói thất bại. Vui lòng kiểm tra log lỗi bên trên.
)
pause
