@echo off
:: VNServerSentinel - Process Watchdog & Self-Healing Loop
:: Tự động hồi sinh tiến trình trong 10 giây nếu bị sập (Tương tự cơ chế WinSW)
cd /d "%~dp0"

:loop
echo [%date% %time%] Khởi chạy VNServerSentinel... >> "data\watchdog.log"
python main.py >> "data\watchdog.log" 2>&1

echo [%date% %time%] Tiến trình bị gián đoạn! Tự động khởi động lại sau 10 giây... >> "data\watchdog.log"
timeout /t 10 /nobreak >nul
goto loop
