@echo off
chcp 65001 >nul
title VNServerSentinel Console
cd /d "%~dp0"
echo ==========================================================
echo    Khởi chạy VNServerSentinel ở chế độ Console trực quan
echo ==========================================================
python main.py
pause
