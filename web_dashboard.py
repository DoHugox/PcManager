"""
VNServerSentinel - Web Dashboard & Remote Management Center
Lightweight, glassmorphic obsidian interface running directly on the PC.
Includes:
- System & Hardware Telemetry (Core i3 5th Gen optimized)
- File Explorer & Web SCP File Transfer (Download, Upload, Preview, Delete, Mkdir)
- Dual-Gate Network Manager (Modem UPnP NAT & Windows Defender Firewall Inbound Rules)
- Versioning & GitHub Auto-Update Watchdog
- Emergency Controls (Webcam, Desktop screenshot, Lock, RustDesk)
"""

import os
import sys
import json
import logging
import platform
import threading
import urllib.parse
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

from config import Config
import system_monitor
import network_upnp
import security_guard
import remote_desktop
import file_manager
import updater

logger = logging.getLogger("VNServerSentinel.WebDashboard")

DASHBOARD_PORT = 8888

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PcManager - Trung Tâm Quản Lý Máy Chủ Từ Xa</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #070a12;
            --bg-surface: rgba(14, 20, 36, 0.75);
            --bg-surface-hover: rgba(22, 31, 56, 0.85);
            --bg-card: rgba(18, 26, 48, 0.6);
            --border-glass: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(0, 242, 254, 0.4);
            
            --accent-cyan: #00f2fe;
            --accent-blue: #4facfe;
            --accent-purple: #7928ca;
            --accent-pink: #ff007f;
            --accent-green: #00e676;
            --accent-amber: #ffab00;
            --accent-red: #ff3366;
            
            --gradient-primary: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            --gradient-accent: linear-gradient(135deg, #7928ca 0%, #ff007f 100%);
            --gradient-card: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
            
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 10% 10%, rgba(0, 242, 254, 0.07) 0%, transparent 45%),
                radial-gradient(circle at 90% 90%, rgba(121, 40, 202, 0.08) 0%, transparent 45%),
                radial-gradient(circle at 50% 50%, rgba(0, 230, 118, 0.03) 0%, transparent 50%);
            background-attachment: fixed;
        }

        .container { max-width: 1440px; margin: 0 auto; padding: 20px 24px; }

        /* Top Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 18px 28px;
            background: var(--bg-surface);
            border: 1px solid var(--border-glass);
            border-radius: 20px;
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            margin-bottom: 22px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        }

        .brand { display: flex; align-items: center; gap: 16px; }
        .logo-box {
            width: 50px; height: 50px;
            background: var(--gradient-primary);
            border-radius: 15px;
            display: flex; align-items: center; justify-content: center;
            font-size: 26px; box-shadow: 0 0 24px rgba(0, 242, 254, 0.45);
        }
        .brand-text h1 {
            font-size: 22px; font-weight: 800; letter-spacing: -0.5px;
            background: linear-gradient(90deg, #fff, #94a3b8);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .brand-text p { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }

        .header-badges { display: flex; align-items: center; gap: 12px; }

        .status-badge {
            display: flex; align-items: center; gap: 8px;
            padding: 6px 14px; border-radius: 30px;
            background: rgba(0, 230, 118, 0.1); border: 1px solid rgba(0, 230, 118, 0.3);
            font-size: 13px; font-weight: 600; color: var(--accent-green);
        }
        .pulse-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: var(--accent-green); box-shadow: 0 0 10px var(--accent-green);
            animation: pulse 2s infinite;
        }

        .version-badge {
            display: flex; align-items: center; gap: 6px;
            padding: 6px 14px; border-radius: 30px;
            background: rgba(121, 40, 202, 0.15); border: 1px solid rgba(121, 40, 202, 0.4);
            font-size: 13px; font-weight: 600; color: #c084fc; cursor: pointer;
            transition: all 0.2s;
        }
        .version-badge:hover {
            background: rgba(121, 40, 202, 0.3);
            transform: scale(1.03);
        }
        .version-badge.has-update {
            background: rgba(255, 171, 0, 0.2);
            border-color: rgba(255, 171, 0, 0.5);
            color: var(--accent-amber);
            animation: pulse-border 2s infinite;
        }

        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        @keyframes pulse-border { 0%, 100% { border-color: rgba(255, 171, 0, 0.5); } 50% { border-color: rgba(255, 0, 127, 0.8); } }

        /* Navigation Tab Bar */
        .nav-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 22px;
            background: var(--bg-surface);
            padding: 8px;
            border-radius: 16px;
            border: 1px solid var(--border-glass);
            backdrop-filter: blur(16px);
            overflow-x: auto;
        }
        .tab-btn {
            display: flex; align-items: center; gap: 10px;
            padding: 10px 20px;
            border-radius: 12px;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            font-size: 14px; font-weight: 600;
            cursor: pointer;
            transition: all 0.25s ease;
            white-space: nowrap;
        }
        .tab-btn:hover {
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.05);
        }
        .tab-btn.active {
            background: var(--gradient-primary);
            color: #050811;
            box-shadow: 0 4px 18px rgba(0, 242, 254, 0.35);
        }

        /* Content Sections */
        .tab-content { display: none; }
        .tab-content.active { display: block; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

        /* General Card Styles */
        .card {
            background: var(--bg-surface);
            border: 1px solid var(--border-glass);
            border-radius: 18px;
            padding: 22px;
            backdrop-filter: blur(20px);
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25);
            transition: all 0.25s ease;
        }
        .card:hover {
            border-color: rgba(255, 255, 255, 0.14);
            transform: translateY(-2px);
        }

        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
        .card-title { font-size: 14px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }

        .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; margin-bottom: 22px; }
        .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 18px; margin-bottom: 22px; }

        /* Typography & Values */
        .ip-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 22px; font-weight: 700;
            color: var(--accent-cyan);
            word-break: break-all;
        }
        .copy-btn {
            background: rgba(255, 255, 255, 0.08); border: 1px solid var(--border-glass);
            color: var(--text-primary); padding: 5px 12px; border-radius: 8px;
            font-size: 12px; font-weight: 500; cursor: pointer; transition: all 0.2s;
        }
        .copy-btn:hover { background: var(--accent-cyan); color: #000; }

        /* Progress Bars */
        .stat-bar-container {
            width: 100%; height: 8px;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 6px; overflow: hidden; margin: 10px 0 6px 0;
        }
        .stat-bar { height: 100%; border-radius: 6px; transition: width 0.5s ease; }
        .bar-cyan { background: var(--gradient-primary); }
        .bar-purple { background: var(--gradient-accent); }
        .bar-green { background: linear-gradient(90deg, #00e676, #1de9b6); }

        /* Button Groups */
        .btn {
            display: inline-flex; align-items: center; justify-content: center; gap: 8px;
            padding: 10px 18px; border-radius: 12px; border: none;
            font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.25s ease;
        }
        .btn-primary { background: var(--gradient-primary); color: #050811; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0, 242, 254, 0.4); }
        .btn-secondary { background: rgba(255, 255, 255, 0.08); border: 1px solid var(--border-glass); color: var(--text-primary); }
        .btn-secondary:hover { background: rgba(255, 255, 255, 0.15); }
        .btn-danger { background: linear-gradient(135deg, #ff3366, #ff007f); color: #fff; }
        .btn-danger:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(255, 51, 102, 0.4); }
        .btn-warning { background: linear-gradient(135deg, #ffab00, #ff8f00); color: #000; }

        /* Quick Action Toolbar */
        .quick-toolbar {
            display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 22px;
        }

        /* Tables */
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th {
            text-align: left; padding: 12px 14px;
            font-size: 12px; font-weight: 600; text-transform: uppercase;
            color: var(--text-muted); border-bottom: 1px solid var(--border-glass);
        }
        td {
            padding: 12px 14px; font-size: 13px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            vertical-align: middle;
        }
        tr:hover td { background: rgba(255, 255, 255, 0.02); }

        .tag-tcp { background: rgba(0, 242, 254, 0.12); color: var(--accent-cyan); padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .tag-udp { background: rgba(121, 40, 202, 0.15); color: #c084fc; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }

        /* ============================================================ */
        /* FILE EXPLORER STYLES */
        /* ============================================================ */
        .explorer-header {
            display: flex; flex-direction: column; gap: 14px; margin-bottom: 16px;
        }
        .drive-selector { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
        .drive-btn {
            background: rgba(255, 255, 255, 0.06); border: 1px solid var(--border-glass);
            color: var(--text-primary); padding: 6px 14px; border-radius: 10px;
            font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;
            display: flex; align-items: center; gap: 6px;
        }
        .drive-btn:hover, .drive-btn.active {
            background: var(--accent-cyan); color: #000; border-color: var(--accent-cyan);
        }

        .breadcrumb-bar {
            display: flex; align-items: center; flex-wrap: wrap; gap: 6px;
            background: rgba(0, 0, 0, 0.35); padding: 10px 16px; border-radius: 12px;
            border: 1px solid var(--border-glass); font-family: 'JetBrains Mono', monospace; font-size: 13px;
        }
        .crumb-item {
            color: var(--accent-cyan); cursor: pointer; text-decoration: underline;
        }
        .crumb-item:hover { color: #fff; }
        .crumb-sep { color: var(--text-muted); }

        .explorer-toolbar {
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
        }
        .search-box {
            display: flex; align-items: center; gap: 8px;
            background: rgba(0, 0, 0, 0.35); border: 1px solid var(--border-glass);
            border-radius: 10px; padding: 6px 14px; flex: 1; max-width: 380px;
        }
        .search-box input {
            background: transparent; border: none; color: #fff; outline: none; width: 100%; font-size: 13px;
        }

        /* Drag & Drop Upload Zone (SCP Style) */
        .upload-dropzone {
            border: 2px dashed rgba(0, 242, 254, 0.35);
            border-radius: 14px;
            padding: 24px;
            text-align: center;
            background: rgba(0, 242, 254, 0.02);
            transition: all 0.25s ease;
            cursor: pointer;
            margin-bottom: 18px;
        }
        .upload-dropzone.dragover {
            border-color: var(--accent-cyan);
            background: rgba(0, 242, 254, 0.08);
            transform: scale(1.005);
        }
        .upload-dropzone p { color: var(--text-secondary); font-size: 13px; margin-top: 6px; }

        .file-icon { font-size: 18px; vertical-align: middle; margin-right: 8px; }
        .file-name-link {
            color: var(--text-primary); text-decoration: none; font-weight: 500; cursor: pointer;
        }
        .file-name-link:hover { color: var(--accent-cyan); text-decoration: underline; }

        /* Snapshots Gallery */
        .gallery-grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px;
        }
        .gallery-item {
            position: relative; border-radius: 14px; overflow: hidden;
            border: 1px solid var(--border-glass); aspect-ratio: 16/10;
            background: #000; cursor: pointer;
        }
        .gallery-item img {
            width: 100%; height: 100%; object-fit: cover;
            transition: transform 0.3s ease;
        }
        .gallery-item:hover img { transform: scale(1.05); }
        .gallery-cap {
            position: absolute; bottom: 0; left: 0; right: 0;
            padding: 8px 10px; background: linear-gradient(transparent, rgba(0,0,0,0.85));
            font-size: 11px; display: flex; justify-content: space-between;
        }

        /* Modal Dialogs */
        .modal {
            display: none; position: fixed; inset: 0;
            background: rgba(0, 0, 0, 0.8); backdrop-filter: blur(8px);
            z-index: 1000; align-items: center; justify-content: center;
        }
        .modal.active { display: flex; animation: fadeIn 0.2s ease; }
        .modal-box {
            background: var(--bg-surface); border: 1px solid var(--border-glass);
            border-radius: 20px; padding: 28px; width: 90%; max-width: 600px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.6); max-height: 85vh; overflow-y: auto;
        }
        .modal-box-large { max-width: 900px; }

        .input-group { margin-bottom: 16px; }
        .input-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
        .input-control {
            width: 100%; padding: 10px 14px; border-radius: 10px;
            background: rgba(0, 0, 0, 0.4); border: 1px solid var(--border-glass);
            color: #fff; font-size: 14px; outline: none; font-family: inherit;
        }
        .input-control:focus { border-color: var(--accent-cyan); }

        pre.code-view {
            background: #04060c; border: 1px solid var(--border-glass);
            border-radius: 12px; padding: 16px; font-family: 'JetBrains Mono', monospace;
            font-size: 12px; max-height: 480px; overflow: auto; color: #a5b4fc; white-space: pre-wrap;
        }

        /* Version / Update Changelog Box */
        .changelog-box {
            background: rgba(0, 0, 0, 0.35); border: 1px solid var(--border-glass);
            border-radius: 14px; padding: 18px; margin-top: 14px;
            font-size: 13px; line-height: 1.6; color: var(--text-secondary);
            max-height: 250px; overflow-y: auto;
        }

        /* Responsive */
        @media (max-width: 768px) {
            header { flex-direction: column; align-items: flex-start; gap: 14px; }
            .grid-3, .grid-2 { grid-template-columns: 1fr; }
            .nav-tabs { flex-wrap: nowrap; overflow-x: auto; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Main Header -->
        <header>
            <div class="brand">
                <div class="logo-box">🛡️</div>
                <div class="brand-text">
                    <h1>PcManager</h1>
                    <p id="system-info">Đang kết nối tới máy chủ...</p>
                </div>
            </div>
            <div class="header-badges">
                <div class="status-badge">
                    <div class="pulse-dot"></div>
                    <span>TRỰC TUYẾN</span>
                </div>
                <div class="version-badge" id="header-version-badge" onclick="switchTab('tab-updates')">
                    <span>🏷️</span>
                    <span id="header-version-text">v1.0.1</span>
                </div>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <div class="nav-tabs">
            <button class="tab-btn active" id="btn-tab-overview" onclick="switchTab('tab-overview')">
                📊 Tổng Quan Hệ Thống
            </button>
            <button class="tab-btn" id="btn-tab-files" onclick="switchTab('tab-files')">
                📁 Quản Lý Tệp & SCP Transfer
            </button>
            <button class="tab-btn" id="btn-tab-network" onclick="switchTab('tab-network')">
                🛡️ Mạng & Tường Lửa (Firewall)
            </button>
            <button class="tab-btn" id="btn-tab-updates" onclick="switchTab('tab-updates')">
                🔄 Phiên Bản & Cập Nhật
            </button>
        </div>

        <!-- ============================================================ -->
        <!-- TAB 1: TỔNG QUAN HỆ THỐNG -->
        <!-- ============================================================ -->
        <div class="tab-content active" id="tab-overview">
            <!-- Quick Action Toolbar -->
            <div class="quick-toolbar">
                <button class="btn btn-primary" onclick="triggerAction('screen')">📸 Chụp Màn Hình Ngay</button>
                <button class="btn btn-primary" style="background: var(--gradient-accent);" onclick="triggerAction('cam')">📷 Chụp Webcam Kẻ Ngồi Máy</button>
                <button class="btn btn-danger" onclick="triggerAction('lock')">🔒 Khóa Màn Hình Lập Tức</button>
                <button class="btn btn-secondary" id="btn-rd-toggle" onclick="toggleRD('on')">🖥️ Bật RustDesk Remote Desktop</button>
            </div>

            <!-- Top Network & Telemetry Cards -->
            <div class="grid-3">
                <!-- WAN IP Card -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">🌐 IP Công Cộng (WAN IP)</span>
                        <button class="copy-btn" onclick="copyText('wan-ip')">Sao chép</button>
                    </div>
                    <div class="ip-value" id="wan-ip">Đang lấy...</div>
                    <p style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
                        Địa chỉ IP từ nhà mạng tại Việt Nam. Tự động cập nhật khi đổi IP.
                    </p>
                </div>

                <!-- LAN IP Card -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">🏠 IP Nội Bộ (LAN IP)</span>
                        <button class="copy-btn" onclick="copyText('lan-ip')">Sao chép</button>
                    </div>
                    <div class="ip-value" id="lan-ip" style="color: var(--accent-blue);">Đang lấy...</div>
                    <p style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
                        Địa chỉ PC trong mạng Wi-Fi gia đình (Dùng để cấu hình Port Forward).
                    </p>
                </div>

                <!-- RustDesk Card -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">⚡ Remote Desktop (RustDesk)</span>
                        <span id="rd-badge" style="font-size: 12px; font-weight: 600; color: var(--text-muted);">Kiểm tra...</span>
                    </div>
                    <div style="font-size: 15px; font-weight: 600;" id="rd-status">Đang kiểm tra...</div>
                    <p style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
                        Chỉ bật khi cần điều khiển màn hình, tự tắt để tiết kiệm RAM cho Core i3.
                    </p>
                </div>
            </div>

            <!-- Hardware Telemetry -->
            <div class="grid-3">
                <!-- CPU -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">💻 Bộ Xử Lý (CPU)</span>
                        <span id="cpu-percent" style="font-weight: 700; color: var(--accent-cyan);">0%</span>
                    </div>
                    <div class="stat-bar-container">
                        <div class="stat-bar bar-cyan" id="cpu-bar" style="width: 0%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-top: 6px;">
                        <span>Intel Core i3 5th Gen</span>
                        <span id="uptime">Uptime: --</span>
                    </div>
                </div>

                <!-- RAM -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">🧠 Bộ Nhớ RAM</span>
                        <span id="ram-percent" style="font-weight: 700; color: var(--accent-purple);">0%</span>
                    </div>
                    <div class="stat-bar-container">
                        <div class="stat-bar bar-purple" id="ram-bar" style="width: 0%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-top: 6px;">
                        <span id="ram-details">0 / 0 GB</span>
                        <span>Tiết kiệm RAM</span>
                    </div>
                </div>

                <!-- Disk -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">💾 Ổ Đĩa Hệ Thống</span>
                        <span id="disk-percent" style="font-weight: 700; color: var(--accent-green);">0%</span>
                    </div>
                    <div class="stat-bar-container">
                        <div class="stat-bar bar-green" id="disk-bar" style="width: 0%;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-top: 6px;">
                        <span id="disk-details">Trống -- GB</span>
                        <span id="boot-time">Khởi động: --</span>
                    </div>
                </div>
            </div>

            <!-- Snapshots Gallery -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🖼️ Hình Ảnh Chụp Gần Đây (Màn hình & Webcam)</div>
                    <button class="copy-btn" onclick="fetchSnapshots()">🔄 Tải Lại Ảnh</button>
                </div>
                <div class="gallery-grid" id="gallery-grid">
                    <p style="color: var(--text-muted); grid-column: 1/-1;">Đang tải danh sách ảnh chụp...</p>
                </div>
            </div>
        </div>

        <!-- ============================================================ -->
        <!-- TAB 2: QUẢN LÝ TỆP & SCP TRANSFER -->
        <!-- ============================================================ -->
        <div class="tab-content" id="tab-files">
            <div class="card">
                <div class="explorer-header">
                    <!-- Drive Letters -->
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                        <div class="drive-selector" id="drive-selector">
                            <span style="font-size: 13px; color: var(--text-muted); font-weight: 600;">Ổ ĐĨA:</span>
                            <!-- Injected via JS -->
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button class="btn btn-secondary" style="padding: 6px 14px; font-size: 13px;" onclick="openModal('modal-mkdir')">📁 Thư Mục Mới</button>
                            <button class="btn btn-primary" style="padding: 6px 14px; font-size: 13px;" onclick="document.getElementById('hidden-file-input').click()">⬆️ Tải Tệp Lên (SCP)</button>
                            <input type="file" id="hidden-file-input" style="display: none;" onchange="handleFileSelect(event)">
                        </div>
                    </div>

                    <!-- Breadcrumbs -->
                    <div class="breadcrumb-bar" id="breadcrumbs-bar">
                        <span class="crumb-item" onclick="loadDirectory('')">Root</span>
                    </div>

                    <!-- Search / Quick Jump Toolbar -->
                    <div class="explorer-toolbar">
                        <div class="search-box">
                            <span>🔍</span>
                            <input type="text" id="file-search-inp" placeholder="Tìm nhanh tệp trong thư mục..." oninput="filterFiles()">
                        </div>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <button class="copy-btn" onclick="goToParentDir()">⬆️ Lên một cấp</button>
                            <button class="copy-btn" onclick="refreshCurrentDir()">🔄 Làm mới</button>
                        </div>
                    </div>
                </div>

                <!-- Drag & Drop Upload Zone -->
                <div class="upload-dropzone" id="upload-dropzone" onclick="document.getElementById('hidden-file-input').click()">
                    <div style="font-size: 28px;">📤</div>
                    <div style="font-weight: 600; font-size: 14px; margin-top: 4px; color: var(--accent-cyan);">
                        Kéo thả tệp tin vào đây để tải lên (SCP Transfer)
                    </div>
                    <p id="upload-status-text">Hoặc bấm vào vùng này để chọn tệp tin từ máy tính Đài Loan của bạn.</p>
                </div>

                <!-- File Table -->
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Tên Tệp / Thư Mục</th>
                                <th>Dung Lượng</th>
                                <th>Ngày Chỉnh Sửa</th>
                                <th style="text-align: right;">Hành Động</th>
                            </tr>
                        </thead>
                        <tbody id="files-tbody">
                            <tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 30px;">Đang tải danh sách tệp...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ============================================================ -->
        <!-- TAB 3: MẠNG & TƯỜNG LỬA (FIREWALL) -->
        <!-- ============================================================ -->
        <div class="tab-content" id="tab-network">
            <div class="card">
                <div class="card-header" style="flex-wrap: wrap; gap: 12px;">
                    <div>
                        <div class="card-title" style="font-size: 16px; margin-bottom: 4px;">
                            🛡️ Quản Lý Hai Cánh Cửa: Modem Router (NAT) & Windows Defender Firewall
                        </div>
                        <p style="font-size: 13px; color: var(--text-secondary);">
                            Để kết nối từ Đài Loan về máy chủ tại Việt Nam, gói tin phải đi qua <strong>2 Cánh Cửa liên hoàn</strong>:
                            1️⃣ <em>Modem Router (UPnP Forwarding)</em> ➔ 2️⃣ <em>Tường Lửa Windows (Inbound Rules)</em>.
                        </p>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-secondary" style="padding: 8px 16px; font-size: 13px;" onclick="openModal('modal-fw')">🧱 Thêm Luật Inbound (Firewall)</button>
                        <button class="btn btn-primary" style="padding: 8px 16px; font-size: 13px;" onclick="openModal('modal-port')">🌐 Mở Cổng Modem (UPnP)</button>
                    </div>
                </div>

                <!-- Subtab Switcher -->
                <div style="display: flex; gap: 10px; margin-top: 14px; border-bottom: 1px solid var(--border-glass); padding-bottom: 10px;">
                    <button class="copy-btn" id="tab-btn-modem" style="background: var(--accent-cyan); color: #000;" onclick="switchPortTab('modem')">
                        🚪 Cửa 1: Cổng Modem Router (UPnP)
                    </button>
                    <button class="copy-btn" id="tab-btn-fw" onclick="switchPortTab('fw')">
                        🧱 Cửa 2: Tường Lửa Windows (Inbound Rules)
                    </button>
                </div>

                <!-- View Cửa 1: Modem -->
                <div id="view-modem" style="margin-top: 12px;">
                    <table>
                        <thead>
                            <tr>
                                <th>Cổng Ngoài (External)</th>
                                <th>Cổng Máy Tính (Internal)</th>
                                <th>Giao Thức</th>
                                <th>Dịch Vụ / Mô Tả</th>
                                <th>Hành Động</th>
                            </tr>
                        </thead>
                        <tbody id="ports-tbody">
                            <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">Đang truy vấn Modem Wi-Fi qua UPnP...</td></tr>
                        </tbody>
                    </table>
                </div>

                <!-- View Cửa 2: Windows Firewall -->
                <div id="view-fw" style="display: none; margin-top: 12px;">
                    <table>
                        <thead>
                            <tr>
                                <th>Tên Luật (Rule Name)</th>
                                <th>Cổng (Port)</th>
                                <th>Hướng (Direction)</th>
                                <th>Giao Thức</th>
                                <th>Hành Động (Action)</th>
                            </tr>
                        </thead>
                        <tbody id="fw-tbody">
                            <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">Đang tải danh sách luật tường lửa...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- ============================================================ -->
        <!-- TAB 4: PHIÊN BẢN & CẬP NHẬT -->
        <!-- ============================================================ -->
        <div class="tab-content" id="tab-updates">
            <div class="grid-2">
                <!-- Version Status Card -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">📦 Thông Tin Phiên Bản</span>
                        <button class="copy-btn" onclick="checkAppUpdate()">🔍 Kiểm Tra Ngay</button>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 12px; margin: 10px 0;">
                        <span style="font-size: 32px; font-weight: 800; color: var(--accent-cyan);" id="app-current-ver">v1.0.1</span>
                        <span id="update-status-badge" style="padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; background: rgba(0, 230, 118, 0.15); color: var(--accent-green);">Bản mới nhất</span>
                    </div>
                    <p style="font-size: 13px; color: var(--text-secondary);">
                        Kho lưu trữ GitHub: <strong id="repo-name" style="color: #fff;">DoHugox/PcManager</strong>
                    </p>
                    <div style="margin-top: 20px; display: flex; gap: 10px;">
                        <button class="btn btn-primary" id="btn-do-update" style="display: none;" onclick="triggerAppUpdate()">⚡ Nâng Cấp Tự Động Ngay</button>
                        <a href="https://github.com/DoHugox/PcManager/releases" target="_blank" class="btn btn-secondary" style="text-decoration: none;">🌐 Mở GitHub Releases</a>
                    </div>
                </div>

                <!-- Changelog Card -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">📝 Ghi Chú Bản Phát Hành (Changelog)</span>
                        <span style="font-size: 12px; color: var(--text-muted);" id="latest-ver-tag">Latest: --</span>
                    </div>
                    <div class="changelog-box" id="changelog-text">
                        Đang lấy thông tin từ GitHub...
                    </div>
                </div>
            </div>

            <!-- Auto-Update & Safe Watchdog Explanation -->
            <div class="card">
                <div class="card-title" style="margin-bottom: 8px;">🛡️ Cơ Chế An Toàn Watchdog Rollback Khi Cập Nhật Từ Xa</div>
                <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.6;">
                    Vì bạn đang ở Đài Loan và không thể cắm màn hình hay bàn phím vào máy chủ ở Việt Nam, hệ thống PcManager trang bị cơ chế bảo vệ tối thượng: 
                    Trước khi cập nhật, toàn bộ mã nguồn phiên bản cũ được sao lưu vào thư mục <code>backup/</code>. Khi bản mới khởi động, tiến trình giám sát chạy đồng hồ đếm ngược 60 giây. Nếu bản cập nhật mới bị lỗi hoặc không kết nối được mạng/Telegram, hệ thống sẽ <strong>tự động khôi phục (rollback)</strong> về bản cũ ngay lập tức để không bao giờ mất kết nối!
                </p>
            </div>
        </div>
    </div>

    <!-- ============================================================ -->
    <!-- MODALS -->
    <!-- ============================================================ -->

    <!-- Modal Mở Port Modem (UPnP) -->
    <div class="modal" id="modal-port">
        <div class="modal-box">
            <h3 style="font-size: 18px; margin-bottom: 16px;">🌐 Mở Cổng Tự Động Trên Modem Wi-Fi (UPnP)</h3>
            <div class="input-group">
                <label>Cổng Ngoài (External Port) - Người từ Đài Loan kết nối vào</label>
                <input type="number" id="inp-ext-port" class="input-control" placeholder="Ví dụ: 8888 hoặc 3389">
            </div>
            <div class="input-group">
                <label>Cổng Trong Máy Tính (Internal Port)</label>
                <input type="number" id="inp-int-port" class="input-control" placeholder="Ví dụ: 8888 hoặc 3389">
            </div>
            <div class="input-group">
                <label>Giao Thức</label>
                <select id="inp-proto" class="input-control">
                    <option value="TCP">TCP (Phổ biến cho Web, RDP, SSH)</option>
                    <option value="UDP">UDP (Game, Streaming)</option>
                </select>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-port')">Hủy</button>
                <button class="btn btn-primary" onclick="submitOpenPort()">Mở Cổng Ngay</button>
            </div>
        </div>
    </div>

    <!-- Modal Mở Tường Lửa Windows (Inbound) -->
    <div class="modal" id="modal-fw">
        <div class="modal-box">
            <h3 style="font-size: 18px; margin-bottom: 16px;">🧱 Thêm Quy Tắc Tường Lửa Windows (Inbound Rule)</h3>
            <div class="input-group">
                <label>Tên Quy Tắc (Rule Name)</label>
                <input type="text" id="inp-fw-name" class="input-control" placeholder="Ví dụ: MyServerPort">
            </div>
            <div class="input-group">
                <label>Cổng Cần Mở (Local Port)</label>
                <input type="number" id="inp-fw-port" class="input-control" placeholder="Ví dụ: 80 hoặc 443">
            </div>
            <div class="input-group">
                <label>Giao Thức</label>
                <select id="inp-fw-proto" class="input-control">
                    <option value="TCP">TCP</option>
                    <option value="UDP">UDP</option>
                </select>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-fw')">Hủy</button>
                <button class="btn btn-primary" onclick="submitOpenFW()">Tạo Luật Inbound</button>
            </div>
        </div>
    </div>

    <!-- Modal Tạo Thư Mục (Mkdir) -->
    <div class="modal" id="modal-mkdir">
        <div class="modal-box">
            <h3 style="font-size: 18px; margin-bottom: 16px;">📁 Tạo Thư Mục Mới</h3>
            <div class="input-group">
                <label>Tên Thư Mục</label>
                <input type="text" id="inp-mkdir-name" class="input-control" placeholder="Ví dụ: BackupData hoặc Projects">
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-mkdir')">Hủy</button>
                <button class="btn btn-primary" onclick="submitMkdir()">Tạo Thư Mục</button>
            </div>
        </div>
    </div>

    <!-- Modal Xem Tệp Văn Bản (File Preview) -->
    <div class="modal" id="modal-preview">
        <div class="modal-box modal-box-large">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h3 style="font-size: 16px; color: var(--accent-cyan);" id="preview-filename">Xem Tệp</h3>
                <button class="copy-btn" onclick="copyPreviewText()">Sao Chép Nội Dung</button>
            </div>
            <pre class="code-view" id="preview-content">Đang tải...</pre>
            <div style="display: flex; justify-content: flex-end; margin-top: 14px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-preview')">Đóng</button>
            </div>
        </div>
    </div>

    <!-- ============================================================ -->
    <!-- JAVASCRIPT LOGIC -->
    <!-- ============================================================ -->
    <script>
        // Tab Navigation
        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            document.getElementById(tabId).classList.add('active');
            if (tabId === 'tab-overview') document.getElementById('btn-tab-overview').classList.add('active');
            if (tabId === 'tab-files') {
                document.getElementById('btn-tab-files').classList.add('active');
                if (!currentPath) loadDirectory('');
            }
            if (tabId === 'tab-network') document.getElementById('btn-tab-network').classList.add('active');
            if (tabId === 'tab-updates') {
                document.getElementById('btn-tab-updates').classList.add('active');
                checkAppUpdate();
            }
        }

        function switchPortTab(tab) {
            if (tab === 'modem') {
                document.getElementById('view-modem').style.display = 'block';
                document.getElementById('view-fw').style.display = 'none';
                document.getElementById('tab-btn-modem').style.background = 'var(--accent-cyan)';
                document.getElementById('tab-btn-modem').style.color = '#000';
                document.getElementById('tab-btn-fw').style.background = 'rgba(255,255,255,0.06)';
                document.getElementById('tab-btn-fw').style.color = 'var(--text-secondary)';
            } else {
                document.getElementById('view-modem').style.display = 'none';
                document.getElementById('view-fw').style.display = 'block';
                document.getElementById('tab-btn-fw').style.background = 'var(--accent-cyan)';
                document.getElementById('tab-btn-fw').style.color = '#000';
                document.getElementById('tab-btn-modem').style.background = 'rgba(255,255,255,0.06)';
                document.getElementById('tab-btn-modem').style.color = 'var(--text-secondary)';
            }
        }

        // ==========================================
        // SYSTEM OVERVIEW LOGIC
        // ==========================================
        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                document.getElementById('system-info').innerText = `${data.net.hostname} - ${data.net.system} (Core i3 5th Gen)`;
                document.getElementById('wan-ip').innerText = data.net.wan_ip;
                document.getElementById('lan-ip').innerText = data.net.lan_ip;
                document.getElementById('rd-status').innerText = data.rd_status;
                
                const isRDActive = data.rd_status.includes("đang hoạt động");
                const rdBadge = document.getElementById('rd-badge');
                const rdBtn = document.getElementById('btn-rd-toggle');
                if (isRDActive) {
                    rdBadge.innerText = "ĐANG BẬT";
                    rdBadge.style.color = "var(--accent-green)";
                    rdBtn.innerText = "⏹️ Tắt RustDesk (Tiết kiệm RAM)";
                    rdBtn.onclick = () => toggleRD('off');
                } else {
                    rdBadge.innerText = "ĐÃ TẮT";
                    rdBadge.style.color = "var(--text-muted)";
                    rdBtn.innerText = "🖥️ Bật RustDesk Remote Desktop";
                    rdBtn.onclick = () => toggleRD('on');
                }

                // Telemetry
                document.getElementById('cpu-percent').innerText = `${data.hw.cpu_percent}%`;
                document.getElementById('cpu-bar').style.width = `${data.hw.cpu_percent}%`;
                
                document.getElementById('ram-percent').innerText = `${data.hw.ram_percent}%`;
                document.getElementById('ram-bar').style.width = `${data.hw.ram_percent}%`;
                document.getElementById('ram-details').innerText = `${data.hw.ram_used_gb} GB / ${data.hw.ram_total_gb} GB`;
                
                if (data.hw.disks && data.hw.disks.length > 0) {
                    const d = data.hw.disks[0];
                    document.getElementById('disk-percent').innerText = `${d.percent}%`;
                    document.getElementById('disk-bar').style.width = `${d.percent}%`;
                    document.getElementById('disk-details').innerText = `Trống ${d.free_gb} GB / ${d.total_gb} GB (${d.mount})`;
                }
                
                document.getElementById('uptime').innerText = `Uptime: ${data.hw.uptime}`;
                document.getElementById('boot-time').innerText = `Khởi động: ${data.hw.boot_time}`;

                fetchPorts();
                fetchFWRules();
                fetchSnapshots();
            } catch (e) {
                console.error("Fetch status error:", e);
            }
        }

        async function fetchSnapshots() {
            try {
                const res = await fetch('/api/snapshots');
                const snaps = await res.json();
                const grid = document.getElementById('gallery-grid');
                if (!snaps || snaps.length === 0) {
                    grid.innerHTML = '<p style="color: var(--text-muted); grid-column: 1/-1;">Chưa có ảnh chụp nào.</p>';
                    return;
                }
                grid.innerHTML = snaps.map(s => `
                    <div class="gallery-item" onclick="window.open('/snapshots/${s.name}', '_blank')">
                        <img src="/snapshots/${s.name}" alt="${s.name}" loading="lazy">
                        <div class="gallery-cap">
                            <span>${s.name.startsWith('cam') ? '📷 Webcam' : '🖥️ Desktop'}</span>
                            <span>${s.time}</span>
                        </div>
                    </div>
                `).join('');
            } catch(e) {}
        }

        async function toggleRD(action) {
            await fetch(`/api/rd?action=${action}`, { method: 'POST' });
            fetchStatus();
        }

        async function triggerAction(act) {
            const res = await fetch(`/api/action?type=${act}`, { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            fetchStatus();
        }

        // ==========================================
        // FILE EXPLORER & WEB SCP TRANSFER
        // ==========================================
        let currentPath = '';
        let parentPath = '';
        let currentItems = [];

        async function loadDirectory(targetPath) {
            try {
                const tbody = document.getElementById('files-tbody');
                tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 30px;">Đang tải danh mục...</td></tr>';
                
                const res = await fetch(`/api/files/list?path=${encodeURIComponent(targetPath || '')}`);
                const data = await res.json();
                
                if (!data.success) {
                    alert("Lỗi: " + data.message);
                    return;
                }
                
                const d = data.data;
                currentPath = d.current_path;
                parentPath = d.parent_path;
                currentItems = d.items;

                // Render Drives
                const driveBox = document.getElementById('drive-selector');
                driveBox.innerHTML = '<span style="font-size: 13px; color: var(--text-muted); font-weight: 600;">Ổ ĐĨA:</span>';
                d.drives.forEach(drv => {
                    const btn = document.createElement('button');
                    btn.className = `drive-btn ${currentPath.startsWith(drv) ? 'active' : ''}`;
                    btn.innerHTML = `💽 ${drv}`;
                    btn.onclick = () => loadDirectory(drv);
                    driveBox.appendChild(btn);
                });

                // Render Breadcrumbs
                const bBox = document.getElementById('breadcrumbs-bar');
                bBox.innerHTML = '';
                d.breadcrumbs.forEach((crumb, idx) => {
                    if (idx > 0) {
                        const sep = document.createElement('span');
                        sep.className = 'crumb-sep';
                        sep.innerText = ' / ';
                        bBox.appendChild(sep);
                    }
                    const cSpan = document.createElement('span');
                    cSpan.className = 'crumb-item';
                    cSpan.innerText = crumb.name;
                    cSpan.onclick = () => loadDirectory(crumb.path);
                    bBox.appendChild(cSpan);
                });

                renderFileTable(currentItems);
            } catch (e) {
                console.error("Load directory error:", e);
            }
        }

        function getFileIcon(cat) {
            switch(cat) {
                case 'folder': return '📁';
                case 'text': return '📝';
                case 'code': return '💻';
                case 'archive': return '📦';
                case 'image': return '🖼️';
                case 'media': return '🎬';
                case 'binary': return '⚙️';
                case 'locked': return '🔒';
                default: return '📄';
            }
        }

        function renderFileTable(items) {
            const tbody = document.getElementById('files-tbody');
            if (!items || items.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 30px;">Thư mục trống.</td></tr>';
                return;
            }

            tbody.innerHTML = items.map(item => {
                const icon = getFileIcon(item.category);
                let nameHtml = '';
                if (item.is_dir) {
                    nameHtml = `<span class="file-name-link" onclick="loadDirectory('${item.path.replace(/\\\\/g, '\\\\\\\\')}')"><strong>${item.name}/</strong></span>`;
                } else {
                    nameHtml = `<span class="file-name-link" onclick="previewFile('${item.path.replace(/\\\\/g, '\\\\\\\\')}')">${item.name}</span>`;
                }

                let actions = '';
                if (!item.is_dir) {
                    actions += `<button class="copy-btn" style="margin-right: 6px;" onclick="downloadFile('${item.path.replace(/\\\\/g, '\\\\\\\\')}')">⬇️ Tải về</button>`;
                    if (['text', 'code'].includes(item.category)) {
                        actions += `<button class="copy-btn" style="margin-right: 6px;" onclick="previewFile('${item.path.replace(/\\\\/g, '\\\\\\\\')}')">👁️ Xem</button>`;
                    }
                }
                actions += `<button class="copy-btn" style="color: var(--accent-red);" onclick="deleteItem('${item.path.replace(/\\\\/g, '\\\\\\\\')}')">🗑️</button>`;

                return `
                    <tr>
                        <td><span class="file-icon">${icon}</span> ${nameHtml}</td>
                        <td style="font-family: monospace; color: var(--text-secondary);">${item.size_formatted}</td>
                        <td style="font-size: 12px; color: var(--text-muted);">${item.mtime}</td>
                        <td style="text-align: right;">${actions}</td>
                    </tr>
                `;
            }).join('');
        }

        function filterFiles() {
            const query = document.getElementById('file-search-inp').value.toLowerCase();
            const filtered = currentItems.filter(i => i.name.toLowerCase().includes(query));
            renderFileTable(filtered);
        }

        function goToParentDir() {
            if (parentPath) loadDirectory(parentPath);
        }

        function refreshCurrentDir() {
            loadDirectory(currentPath);
        }

        function downloadFile(filePath) {
            window.open(`/api/files/download?path=${encodeURIComponent(filePath)}`, '_blank');
        }

        async function previewFile(filePath) {
            const modal = document.getElementById('modal-preview');
            const pre = document.getElementById('preview-content');
            const title = document.getElementById('preview-filename');
            title.innerText = filePath.split(/[\\\\/]/).pop();
            pre.innerText = "Đang tải nội dung...";
            openModal('modal-preview');

            const res = await fetch(`/api/files/view?path=${encodeURIComponent(filePath)}`);
            const data = await res.json();
            if (data.success) {
                pre.innerText = data.content;
            } else {
                pre.innerText = "Không thể xem trước tệp: " + data.content;
            }
        }

        function copyPreviewText() {
            const text = document.getElementById('preview-content').innerText;
            navigator.clipboard.writeText(text);
            alert("Đã sao chép nội dung tệp vào clipboard!");
        }

        async function deleteItem(filePath) {
            const name = filePath.split(/[\\\\/]/).pop();
            if (!confirm(`Bạn có chắc chắn muốn xóa vĩnh viễn: "${name}" không?`)) return;
            const res = await fetch(`/api/files/delete?path=${encodeURIComponent(filePath)}`, { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            refreshCurrentDir();
        }

        async function submitMkdir() {
            const name = document.getElementById('inp-mkdir-name').value.trim();
            if (!name) { alert("Vui lòng nhập tên thư mục!"); return; }
            const newPath = currentPath + (currentPath.endsWith('\\\\') || currentPath.endsWith('/') ? '' : '/') + name;
            const res = await fetch(`/api/files/mkdir?path=${encodeURIComponent(newPath)}`, { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            closeModal('modal-mkdir');
            refreshCurrentDir();
        }

        // Web SCP Drag & Drop Upload
        const dropzone = document.getElementById('upload-dropzone');
        ['dragenter', 'dragover'].forEach(e => {
            dropzone.addEventListener(e, (evt) => {
                evt.preventDefault(); evt.stopPropagation();
                dropzone.classList.add('dragover');
            });
        });
        ['dragleave', 'drop'].forEach(e => {
            dropzone.addEventListener(e, (evt) => {
                evt.preventDefault(); evt.stopPropagation();
                dropzone.classList.remove('dragover');
            });
        });

        dropzone.addEventListener('drop', (evt) => {
            const files = evt.dataTransfer.files;
            if (files.length > 0) uploadSingleFile(files[0]);
        });

        function handleFileSelect(evt) {
            const files = evt.target.files;
            if (files.length > 0) uploadSingleFile(files[0]);
        }

        async function uploadSingleFile(file) {
            const statusText = document.getElementById('upload-status-text');
            statusText.innerText = `⏳ Đang tải lên (SCP Transfer): ${file.name} (${(file.size / 1024).toFixed(1)} KB)...`;
            try {
                const res = await fetch(`/api/files/upload?dir=${encodeURIComponent(currentPath)}&filename=${encodeURIComponent(file.name)}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/octet-stream' },
                    body: file
                });
                const data = await res.json();
                alert(data.message);
                statusText.innerText = "Hoặc bấm vào vùng này để chọn tệp tin từ máy tính Đài Loan của bạn.";
                refreshCurrentDir();
            } catch(e) {
                alert("Lỗi tải lên: " + e);
                statusText.innerText = "Lỗi tải lên. Hãy thử lại.";
            }
        }

        // ==========================================
        // NETWORK & FIREWALL LOGIC
        // ==========================================
        async function fetchPorts() {
            try {
                const res = await fetch('/api/ports');
                const ports = await res.json();
                const tbody = document.getElementById('ports-tbody');
                if (!ports || ports.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">Chưa có cổng nào mở qua UPnP. Bấm "+ Mở Cổng Modem (UPnP)" để mở.</td></tr>';
                    return;
                }
                tbody.innerHTML = ports.map(p => `
                    <tr>
                        <td><strong style="font-size: 15px; color: var(--accent-cyan);">${p.external_port || p.externalPort}</strong></td>
                        <td>${p.internal_port || p.internalPort || '-'}</td>
                        <td><span class="tag-${(p.protocol || 'TCP').toLowerCase()}">${p.protocol || 'TCP'}</span></td>
                        <td>${p.description || 'PcManager Service'}</td>
                        <td><button class="copy-btn" onclick="closePort(${p.external_port || p.externalPort}, '${p.protocol || 'TCP'}')">Đóng Cổng</button></td>
                    </tr>
                `).join('');
            } catch(e) {}
        }

        async function fetchFWRules() {
            try {
                const res = await fetch('/api/fw/rules');
                const rules = await res.json();
                const tbody = document.getElementById('fw-tbody');
                if (!rules || rules.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">Chưa có luật riêng nào. Bấm "Thêm Luật Inbound" để tạo.</td></tr>';
                    return;
                }
                tbody.innerHTML = rules.map(r => `
                    <tr>
                        <td><strong>${r.name}</strong></td>
                        <td><span style="font-family: monospace; color: var(--accent-cyan); font-weight: bold; font-size: 14px;">${r.port}</span></td>
                        <td><span style="color: var(--accent-green); font-weight: 600;">Inbound (Vào)</span></td>
                        <td><span class="tag-${r.proto.toLowerCase().includes('udp') ? 'udp' : 'tcp'}">${r.proto}</span></td>
                        <td><span style="color: var(--accent-green); font-size: 13px;">✅ Cho phép (${r.action})</span></td>
                    </tr>
                `).join('');
            } catch(e) {}
        }

        async function submitOpenPort() {
            const ext = document.getElementById('inp-ext-port').value;
            const intP = document.getElementById('inp-int-port').value;
            const proto = document.getElementById('inp-proto').value;
            if (!ext || !intP) { alert("Vui lòng nhập đầy đủ cổng ngoài và cổng trong!"); return; }
            
            const res = await fetch(`/api/ports/open?ext=${ext}&int=${intP}&proto=${proto}`, { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            closeModal('modal-port');
            fetchPorts();
            fetchFWRules();
        }

        async function closePort(port, proto) {
            if (!confirm(`Bạn có chắc muốn đóng port ${port} (${proto}) không?`)) return;
            const res = await fetch(`/api/ports/close?ext=${port}&proto=${proto}`, { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            fetchPorts();
        }

        async function submitOpenFW() {
            const name = document.getElementById('inp-fw-name').value;
            const port = document.getElementById('inp-fw-port').value;
            const proto = document.getElementById('inp-fw-proto').value;
            if (!port) { alert("Vui lòng nhập số cổng!"); return; }
            const res = await fetch(`/api/fw/open?name=${encodeURIComponent(name)}&port=${port}&proto=${proto}`, { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            closeModal('modal-fw');
            fetchFWRules();
        }

        // ==========================================
        // VERSION & UPDATE LOGIC
        // ==========================================
        async function checkAppUpdate() {
            try {
                const res = await fetch('/api/version');
                const data = await res.json();
                
                document.getElementById('app-current-ver').innerText = `v${data.current_version}`;
                document.getElementById('header-version-text').innerText = `v${data.current_version}`;
                document.getElementById('repo-name').innerText = data.repo;
                document.getElementById('latest-ver-tag').innerText = `Latest: v${data.latest_version}`;

                const badge = document.getElementById('update-status-badge');
                const headerBadge = document.getElementById('header-version-badge');
                const btnUpdate = document.getElementById('btn-do-update');
                const clBox = document.getElementById('changelog-text');

                if (data.release_notes) {
                    clBox.innerText = data.release_notes;
                }

                if (data.has_update) {
                    badge.innerText = `Có bản mới: v${data.latest_version}!`;
                    badge.style.background = 'rgba(255, 171, 0, 0.2)';
                    badge.style.color = 'var(--accent-amber)';
                    headerBadge.classList.add('has-update');
                    headerBadge.title = `Có bản cập nhật mới v${data.latest_version}`;
                    btnUpdate.style.display = 'inline-flex';
                } else {
                    badge.innerText = "Đã là bản mới nhất";
                    badge.style.background = 'rgba(0, 230, 118, 0.15)';
                    badge.style.color = 'var(--accent-green)';
                    headerBadge.classList.remove('has-update');
                    btnUpdate.style.display = 'none';
                }
            } catch(e) {
                console.error("Check update error:", e);
            }
        }

        async function triggerAppUpdate() {
            if (!confirm("Hệ thống sẽ tải bản cập nhật mới, tự sao lưu và khởi động lại. Bạn có muốn tiếp tục không?")) return;
            const res = await fetch('/api/update', { method: 'POST' });
            const data = await res.json();
            alert(data.message);
        }

        // Utilities
        function copyText(elemId) {
            const text = document.getElementById(elemId).innerText;
            navigator.clipboard.writeText(text);
            alert("Đã sao chép: " + text);
        }
        function openModal(id) { document.getElementById(id).classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }

        // Initial Load & Heartbeat
        fetchStatus();
        checkAppUpdate();
        setInterval(fetchStatus, 5000);
    </script>
</body>
</html>
"""

# In-memory firewall rules tracker + system query
FIREWALL_RULES_STORE = [
    {"name": "VNServerSentinel_WebUI", "port": "8888", "proto": "TCP", "action": "Allow"},
    {"name": "VNServerSentinel_RDP", "port": "3389", "proto": "TCP", "action": "Allow"},
    {"name": "VNServerSentinel_RustDesk", "port": "21115-21119", "proto": "TCP/UDP", "action": "Allow"}
]

def add_custom_firewall_rule(name: str, port: int, protocol: str = "TCP") -> tuple[bool, str]:
    """Create an Inbound Rule in Windows Defender Firewall via netsh."""
    rule_name = name.strip() or f"VNServerSentinel_Custom_{port}"
    protocol = protocol.upper()
    
    FIREWALL_RULES_STORE.append({
        "name": rule_name,
        "port": str(port),
        "proto": protocol,
        "action": "Allow"
    })
    
    if platform.system().lower() != "windows":
        return True, f"[Mô phỏng] Đã tạo Inbound Rule '{rule_name}' trên Windows Firewall (Port {port}/{protocol})"
        
    try:
        cmd = f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=allow protocol={protocol} localport={port}'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            return True, f"✅ Đã tạo Inbound Rule '{rule_name}' (Port {port}/{protocol}) trên Windows Defender Firewall thành công!"
        return False, f"⚠️ netsh trả về lỗi: {res.stderr or res.stdout}"
    except Exception as e:
        return False, f"Lỗi khi cấu hình Windows Firewall: {e}"

class DashboardRequestHandler(BaseHTTPRequestHandler):
    upnp_mgr = None

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        params = urllib.parse.parse_qs(url.query)

        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        elif path == "/api/status":
            net = network_upnp.get_network_info()
            hw = system_monitor.get_hardware_status()
            rd = remote_desktop.get_remote_desktop_status()
            data = {"net": net, "hw": hw, "rd_status": rd}
            self._send_json(data)

        elif path == "/api/ports":
            ports = []
            if self.upnp_mgr:
                ports = self.upnp_mgr.list_ports()
            self._send_json(ports)

        elif path == "/api/fw/rules":
            self._send_json(FIREWALL_RULES_STORE)

        elif path == "/api/version":
            info = updater.get_version_info()
            self._send_json(info)

        # File Explorer GET endpoints
        elif path == "/api/files/list":
            target_path = params.get("path", [""])[0]
            ok, data, msg = file_manager.list_directory_web(target_path)
            self._send_json({"success": ok, "data": data, "message": msg})

        elif path == "/api/files/view":
            target_path = params.get("path", [""])[0]
            ok, content = file_manager.read_text_file(target_path, max_lines=300)
            self._send_json({"success": ok, "content": content})

        elif path == "/api/files/download":
            target_path = params.get("path", [""])[0]
            p = Path(target_path).resolve()
            if p.exists() and p.is_file():
                try:
                    file_size = p.stat().st_size
                    filename = p.name
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    # RFC 5987 / URL encoded filename
                    safe_name = urllib.parse.quote(filename)
                    self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"; filename*=UTF-8\'\'{safe_name}')
                    self.send_header("Content-Length", str(file_size))
                    self.end_headers()

                    # Stream file chunk-by-chunk (64KB buffer) to prevent RAM overload on Core i3
                    with open(p, "rb") as f:
                        while True:
                            chunk = f.read(64 * 1024)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                    return
                except Exception as e:
                    logger.error(f"Download stream error: {e}")
                    self.send_error(500, f"Error streaming file: {e}")
            else:
                self.send_error(404, "File not found")

        elif path == "/api/snapshots":
            snaps = []
            if Config.SNAPSHOT_DIR.exists():
                for f in sorted(Config.SNAPSHOT_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:12]:
                    if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                        snaps.append({
                            "name": f.name,
                            "time": f.name.split("_")[1] if "_" in f.name else ""
                        })
            self._send_json(snaps)

        elif path.startswith("/snapshots/"):
            fname = Path(path).name
            file_path = Config.SNAPSHOT_DIR / fname
            if file_path.exists() and file_path.is_file():
                self.send_response(200)
                self.send_header("Content-type", "image/jpeg")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(url.query)

        if url.path == "/api/rd":
            action = params.get("action", [""])[0]
            if action == "on":
                ok, msg = remote_desktop.start_remote_desktop()
            else:
                ok, msg = remote_desktop.stop_remote_desktop()
            self._send_json({"success": ok, "message": msg})

        elif url.path == "/api/action":
            act_type = params.get("type", [""])[0]
            if act_type == "screen":
                p, msg = security_guard.capture_screenshot()
            elif act_type == "cam":
                p, msg = security_guard.capture_webcam()
            elif act_type == "lock":
                ok, msg = security_guard.lock_workstation()
            else:
                msg = "Hành động không xác định"
            self._send_json({"message": msg})

        elif url.path == "/api/ports/open":
            ext = int(params.get("ext", [0])[0])
            int_p = int(params.get("int", [0])[0])
            proto = params.get("proto", ["TCP"])[0]
            if self.upnp_mgr:
                ok, msg = self.upnp_mgr.open_port(ext, int_p, protocol=proto)
            else:
                ok, msg = False, "UPnP Manager chưa sẵn sàng."
            self._send_json({"success": ok, "message": msg})

        elif url.path == "/api/ports/close":
            ext = int(params.get("ext", [0])[0])
            proto = params.get("proto", ["TCP"])[0]
            if self.upnp_mgr:
                ok, msg = self.upnp_mgr.close_port(ext, protocol=proto)
            else:
                ok, msg = False, "UPnP Manager chưa sẵn sàng."
            self._send_json({"success": ok, "message": msg})

        elif url.path == "/api/fw/open":
            name = params.get("name", [""])[0]
            port = int(params.get("port", [0])[0])
            proto = params.get("proto", ["TCP"])[0]
            ok, msg = add_custom_firewall_rule(name, port, proto)
            self._send_json({"success": ok, "message": msg})

        # File Explorer POST endpoints
        elif url.path == "/api/files/upload":
            target_dir = params.get("dir", [""])[0]
            filename = params.get("filename", [""])[0]
            if not target_dir or not filename:
                self._send_json({"success": False, "message": "Thiếu thư mục đích hoặc tên tệp."})
                return
            try:
                dest_dir = Path(target_dir).resolve()
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = dest_dir / filename

                content_len = int(self.headers.get("Content-Length", 0))
                remaining = content_len
                chunk_size = 64 * 1024

                # Stream upload chunk-by-chunk to disk without ballooning memory
                with open(dest_file, "wb") as f:
                    while remaining > 0:
                        to_read = min(chunk_size, remaining)
                        buf = self.rfile.read(to_read)
                        if not buf:
                            break
                        f.write(buf)
                        remaining -= len(buf)

                self._send_json({"success": True, "message": f"✅ Đã tải lên tệp '{filename}' thành công!"})
            except Exception as e:
                logger.error(f"File upload error: {e}")
                self._send_json({"success": False, "message": f"Lỗi khi lưu tệp: {e}"})

        elif url.path == "/api/files/mkdir":
            target_path = params.get("path", [""])[0]
            ok, msg = file_manager.make_directory(target_path)
            self._send_json({"success": ok, "message": msg})

        elif url.path == "/api/files/delete":
            target_path = params.get("path", [""])[0]
            ok, msg = file_manager.delete_path(target_path)
            self._send_json({"success": ok, "message": msg})

        elif url.path == "/api/update":
            has_update, new_ver, dl_url, notes = updater.check_github_update()
            if not has_update:
                self._send_json({"success": False, "message": "Hiện tại bạn đang ở phiên bản mới nhất."})
            else:
                self._send_json({"success": True, "message": f"Đang chuẩn bị cập nhật lên v{new_ver}..."})

    def _send_json(self, data: dict | list):
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress standard HTTP request logging in stdout
        pass

def start_dashboard_server(upnp_mgr, port: int = DASHBOARD_PORT) -> threading.Thread:
    """Run Web Dashboard in a daemon background thread."""
    DashboardRequestHandler.upnp_mgr = upnp_mgr
    server = HTTPServer(("0.0.0.0", port), DashboardRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"🚀 PcManager Web Dashboard is running at http://localhost:{port}")
    return thread
