@echo off
:: VNServerSentinel - Process Watchdog & Self-Healing Loop
:: Tự động hồi sinh tiến trình trong 10 giây nếu bị sập (Tương tự cơ chế WinSW)
cd /d "%~dp0"

:loop
if exist "PcManager.exe" (
    echo [%date% %time%] Khởi chạy PcManager.exe độc lập... >> "data\watchdog.log"
    PcManager.exe >> "data\watchdog.log" 2>&1
) else (
    echo [%date% %time%] Khởi chạy Python main.py... >> "data\watchdog.log"
    python main.py >> "data\watchdog.log" 2>&1
)

echo [%date% %time%] Tiến trình bị gián đoạn! Tự động khởi động lại sau 10 giây... >> "data\watchdog.log"
timeout /t 10 /nobreak >nul
goto loop
