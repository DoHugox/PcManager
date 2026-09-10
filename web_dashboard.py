"""
VNServerSentinel / PcManager - Modern Glassmorphic Web Dashboard
Embedded lightweight web server providing an ultra-premium dark mode UI
accessible both locally on Windows and remotely from Taiwan.
"""

import os
import sys
import json
import socket
import logging
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional

from config import Config
import network_upnp
import system_monitor
import security_guard
import file_manager
import remote_desktop

logger = logging.getLogger("VNServerSentinel.WebDashboard")

DASHBOARD_PORT = 8888

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PcManager - Server Guardian Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0a0e17;
            --bg-surface: rgba(18, 26, 43, 0.75);
            --bg-card: rgba(26, 38, 63, 0.6);
            --border-glass: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(0, 242, 254, 0.3);
            --text-primary: #f0f4fc;
            --text-secondary: #8c9cb8;
            --text-muted: #536482;
            --accent-cyan: #00f2fe;
            --accent-blue: #4facfe;
            --accent-green: #00e676;
            --accent-red: #ff3366;
            --accent-yellow: #ffd600;
            --accent-purple: #7928ca;
            --gradient-cyan: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
            --gradient-danger: linear-gradient(135deg, #ff0844 0%, #ffb199 100%);
            --gradient-card: linear-gradient(145deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Outfit', sans-serif; }

        body {
            background-color: var(--bg-base);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(0, 242, 254, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 85% 85%, rgba(121, 40, 202, 0.08) 0%, transparent 40%);
        }

        .container { max-width: 1400px; margin: 0 auto; padding: 24px; }

        /* Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 30px;
            background: var(--bg-surface);
            border: 1px solid var(--border-glass);
            border-radius: 20px;
            backdrop-filter: blur(16px);
            margin-bottom: 28px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }

        .brand { display: flex; align-items: center; gap: 16px; }
        .logo-box {
            width: 48px; height: 48px;
            background: var(--gradient-cyan);
            border-radius: 14px;
            display: flex; align-items: center; justify-content: center;
            font-size: 24px; box-shadow: 0 0 20px rgba(0, 242, 254, 0.4);
        }
        .brand-text h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }
        .brand-text p { font-size: 13px; color: var(--text-secondary); }

        .header-actions { display: flex; align-items: center; gap: 14px; }
        .status-badge {
            display: flex; align-items: center; gap: 8px;
            padding: 8px 16px; border-radius: 30px;
            background: rgba(0, 230, 118, 0.1); border: 1px solid rgba(0, 230, 118, 0.3);
            font-size: 13px; font-weight: 600; color: var(--accent-green);
        }
        .pulse-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: var(--accent-green); box-shadow: 0 0 10px var(--accent-green);
            animation: pulse 2s infinite;
        }

        /* Top IP & Network Cards */
        .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 28px; }
        
        .card {
            background: var(--bg-surface);
            border: 1px solid var(--border-glass);
            border-radius: 20px;
            padding: 24px;
            backdrop-filter: blur(16px);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        .card:hover {
            border-color: var(--border-glow);
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(0, 242, 254, 0.1);
        }

        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .card-title { font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary); font-weight: 600; }
        .card-icon { font-size: 20px; }

        .ip-value {
            font-size: 28px; font-weight: 700; letter-spacing: -0.5px;
            color: var(--text-primary); margin-bottom: 8px;
            display: flex; align-items: center; justify-content: space-between;
        }
        .copy-btn {
            background: rgba(255,255,255,0.06); border: 1px solid var(--border-glass);
            color: var(--text-secondary); padding: 6px 12px; border-radius: 8px;
            font-size: 12px; cursor: pointer; transition: all 0.2s;
        }
        .copy-btn:hover { background: var(--accent-cyan); color: #000; }

        /* Hardware Metrics Grid */
        .hardware-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 28px; }
        .metric-card {
            background: var(--bg-surface); border: 1px solid var(--border-glass);
            border-radius: 20px; padding: 20px; backdrop-filter: blur(16px);
        }
        .metric-val { font-size: 32px; font-weight: 700; margin: 10px 0; color: #fff; }
        .progress-bar-bg { width: 100%; height: 8px; background: rgba(255,255,255,0.06); border-radius: 10px; overflow: hidden; }
        .progress-bar-fill { height: 100%; background: var(--gradient-cyan); border-radius: 10px; transition: width 0.5s ease; }

        /* Actions Bar */
        .actions-section { margin-bottom: 28px; }
        .section-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 10px; }
        .action-buttons { display: flex; flex-wrap: wrap; gap: 14px; }
        
        .btn {
            display: inline-flex; align-items: center; gap: 10px;
            padding: 12px 22px; border-radius: 12px;
            font-size: 14px; font-weight: 600; cursor: pointer;
            border: none; transition: all 0.25s ease;
        }
        .btn-primary { background: var(--gradient-cyan); color: #0a0e17; box-shadow: 0 4px 15px rgba(0,242,254,0.3); }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,242,254,0.5); }
        .btn-danger { background: var(--gradient-danger); color: #fff; box-shadow: 0 4px 15px rgba(255,8,68,0.3); }
        .btn-danger:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255,8,68,0.5); }
        .btn-secondary { background: rgba(255,255,255,0.06); color: var(--text-primary); border: 1px solid var(--border-glass); }
        .btn-secondary:hover { background: rgba(255,255,255,0.12); }

        /* Tables & Port Manager */
        .table-card {
            background: var(--bg-surface); border: 1px solid var(--border-glass);
            border-radius: 20px; padding: 24px; margin-bottom: 28px;
        }
        table { width: 100%; border-collapse: collapse; margin-top: 14px; }
        th { text-align: left; padding: 12px 16px; color: var(--text-secondary); font-size: 13px; text-transform: uppercase; border-bottom: 1px solid var(--border-glass); }
        td { padding: 14px 16px; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 14px; }
        tr:last-child td { border-bottom: none; }

        .tag-tcp { background: rgba(79, 172, 254, 0.15); color: var(--accent-blue); padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 12px; }
        .tag-udp { background: rgba(255, 214, 0, 0.15); color: var(--accent-yellow); padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 12px; }

        /* Snapshots Gallery */
        .gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; margin-top: 16px; }
        .gallery-item {
            border-radius: 14px; overflow: hidden; border: 1px solid var(--border-glass);
            background: rgba(0,0,0,0.3); position: relative;
        }
        .gallery-item img { width: 100%; height: 160px; object-fit: cover; display: block; }
        .gallery-cap { padding: 10px; font-size: 12px; color: var(--text-secondary); display: flex; justify-content: space-between; }

        /* Modal */
        .modal {
            display: none; position: fixed; inset: 0;
            background: rgba(0,0,0,0.75); backdrop-filter: blur(8px);
            align-items: center; justify-content: center; z-index: 100;
        }
        .modal.active { display: flex; }
        .modal-box {
            background: #151d2f; border: 1px solid var(--border-glass);
            border-radius: 20px; padding: 28px; width: 100%; max-width: 480px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        .input-group { margin-bottom: 16px; }
        .input-group label { display: block; font-size: 13px; color: var(--text-secondary); margin-bottom: 6px; font-weight: 500; }
        .input-control {
            width: 100%; padding: 12px 14px; border-radius: 10px;
            background: rgba(255,255,255,0.04); border: 1px solid var(--border-glass);
            color: #fff; font-size: 14px; outline: none;
        }
        .input-control:focus { border-color: var(--accent-cyan); }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 230, 118, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 230, 118, 0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header>
            <div class="brand">
                <div class="logo-box">🛡️</div>
                <div class="brand-text">
                    <h1>PcManager Dashboard</h1>
                    <p id="system-info">Đang kết nối tới máy chủ...</p>
                </div>
            </div>
            <div class="header-actions">
                <div class="status-badge">
                    <span class="pulse-dot"></span>
                    <span>ONLINE (VIỆT NAM)</span>
                </div>
                <button class="btn btn-secondary" onclick="fetchStatus()">🔄 Làm Mới</button>
            </div>
        </header>

        <!-- Top IP Cards -->
        <div class="grid-3">
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🌍 Public WAN IP (Đổi Tự Động)</span>
                    <span class="card-icon">🌐</span>
                </div>
                <div class="ip-value">
                    <span id="wan-ip">Đang dò...</span>
                    <button class="copy-btn" onclick="copyText('wan-ip')">Copy</button>
                </div>
                <p style="font-size: 12px; color: var(--text-secondary);">IP công cộng để kết nối trực tiếp từ Đài Loan.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">🏠 Local LAN IP (Wi-Fi Nhà)</span>
                    <span class="card-icon">📶</span>
                </div>
                <div class="ip-value">
                    <span id="lan-ip">Đang dò...</span>
                    <button class="copy-btn" onclick="copyText('lan-ip')">Copy</button>
                </div>
                <p style="font-size: 12px; color: var(--text-secondary);">IP nội mạng của máy chủ trên Modem Router.</p>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-title">🖥️ Remote Desktop (RustDesk)</span>
                    <span class="card-icon">⚡</span>
                </div>
                <div class="ip-value" style="font-size: 20px;">
                    <span id="rd-status">Đang kiểm tra...</span>
                </div>
                <div style="margin-top: 10px;">
                    <button class="btn btn-primary" style="padding: 6px 14px; font-size: 12px;" onclick="toggleRD('on')">Bật RustDesk</button>
                    <button class="btn btn-secondary" style="padding: 6px 14px; font-size: 12px;" onclick="toggleRD('off')">Tắt (Tiết Kiệm RAM)</button>
                </div>
            </div>
        </div>

        <!-- Hardware Gauges -->
        <div class="hardware-grid">
            <div class="metric-card">
                <div class="card-title">CPU (Intel Core i3)</div>
                <div class="metric-val" id="cpu-percent">0%</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="cpu-bar" style="width: 0%;"></div></div>
            </div>
            <div class="metric-card">
                <div class="card-title">Bộ Nhớ RAM</div>
                <div class="metric-val" id="ram-percent">0%</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="ram-bar" style="width: 0%; background: linear-gradient(135deg, #ffd600, #ff9100);"></div></div>
                <p id="ram-details" style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">0 GB / 0 GB</p>
            </div>
            <div class="metric-card">
                <div class="card-title">Dung Lượng Ổ C:</div>
                <div class="metric-val" id="disk-percent">0%</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="disk-bar" style="width: 0%; background: linear-gradient(135deg, #00e676, #00b0ff);"></div></div>
                <p id="disk-details" style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">Trống 0 GB</p>
            </div>
            <div class="metric-card">
                <div class="card-title">Thời Gian Chạy (Uptime)</div>
                <div class="metric-val" id="uptime" style="font-size: 22px;">0 phút</div>
                <p id="boot-time" style="font-size: 12px; color: var(--text-secondary); margin-top: 14px;">Khởi động: --</p>
            </div>
        </div>

        <!-- Quick Control Actions -->
        <div class="actions-section">
            <div class="section-title">⚡ Thao Tác Nhanh Trực Tiếp</div>
            <div class="action-buttons">
                <button class="btn btn-primary" onclick="triggerAction('screen')">📸 Chụp Màn Hình Ngay</button>
                <button class="btn btn-primary" onclick="triggerAction('cam')">📷 Chụp Webcam Kẻ Ngồi Máy</button>
                <button class="btn btn-danger" onclick="triggerAction('lock')">🔒 Khóa Màn Hình Lập Tức</button>
                <button class="btn btn-secondary" onclick="openModal('modal-port')">🚪 Mở Port Router (UPnP)</button>
            </div>
        </div>

        <!-- Router UPnP Port Forwarding & Windows Firewall Table -->
        <div class="table-card">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <div class="section-title" style="margin-bottom: 4px;">🛡️ Quản Lý Cổng: Modem Router (NAT) & Tường Lửa Windows (Firewall)</div>
                    <p style="font-size: 13px; color: var(--text-secondary);">
                        Để kết nối từ Đài Loan về máy tính ở VN, gói tin phải đi qua <strong>2 Cánh Cửa</strong>: 
                        1️⃣ <em>Modem Router (UPnP)</em> ➔ 2️⃣ <em>Windows Firewall (Inbound Rules)</em>. 
                        Hệ thống tự động đồng bộ cả 2 cánh cửa này cùng lúc!
                    </p>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-secondary" style="padding: 8px 16px; font-size: 13px;" onclick="openModal('modal-fw')">🧱 Mở Tường Lửa Windows (Inbound)</button>
                    <button class="btn btn-primary" style="padding: 8px 16px; font-size: 13px;" onclick="openModal('modal-port')">🌐 Mở Cổng Modem (UPnP)</button>
                </div>
            </div>

            <!-- Tab Switcher -->
            <div style="display: flex; gap: 10px; margin-top: 18px; border-bottom: 1px solid var(--border-glass); padding-bottom: 10px;">
                <button class="copy-btn" id="tab-btn-modem" style="background: var(--accent-cyan); color: #000;" onclick="switchPortTab('modem')">Cửa 1: Cổng Modem Router (UPnP)</button>
                <button class="copy-btn" id="tab-btn-fw" onclick="switchPortTab('fw')">Cửa 2: Tường Lửa Windows (Inbound Rules)</button>
            </div>

            <div id="view-modem">
                <table>
                    <thead>
                        <tr>
                            <th>Cổng Ngoài (External)</th>
                            <th>Cổng Máy Tính (Internal)</th>
                            <th>Giao Thức</th>
                            <th>Trạng Thái Windows Firewall</th>
                            <th>Hành Động</th>
                        </tr>
                    </thead>
                    <tbody id="ports-tbody">
                        <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Đang truy vấn Modem Wi-Fi qua UPnP...</td></tr>
                    </tbody>
                </table>
            </div>

            <div id="view-fw" style="display: none;">
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
                        <tr>
                            <td><strong>VNServerSentinel_Web</strong></td>
                            <td>8888</td>
                            <td><span style="color: var(--accent-green); font-weight: 600;">Inbound (Vào)</span></td>
                            <td><span class="tag-tcp">TCP</span></td>
                            <td><span style="color: var(--accent-green);">Đang Cho Phép (Allow)</span></td>
                        </tr>
                        <tr>
                            <td><strong>VNServerSentinel_RDP</strong></td>
                            <td>3389</td>
                            <td><span style="color: var(--accent-green); font-weight: 600;">Inbound (Vào)</span></td>
                            <td><span class="tag-tcp">TCP</span></td>
                            <td><span style="color: var(--accent-green);">Đang Cho Phép (Allow)</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Snapshots Gallery -->
        <div class="table-card">
            <div class="section-title">🖼️ Hình Ảnh Chụp Gần Đây (Màn hình / Webcam)</div>
            <div class="gallery-grid" id="gallery-grid">
                <p style="color: var(--text-muted);">Chưa có ảnh chụp nào.</p>
            </div>
        </div>
    </div>

    <!-- Modal Mở Port -->
    <div class="modal" id="modal-port">
        <div class="modal-box">
            <h3 style="font-size: 18px; margin-bottom: 16px;">🚪 Mở Cổng Router Mới (UPnP)</h3>
            <div class="input-group">
                <label>Cổng Ngoài (External Port)</label>
                <input type="number" id="inp-ext-port" class="input-control" placeholder="Ví dụ: 8080">
            </div>
            <div class="input-group">
                <label>Cổng Trong Máy Tính (Internal Port)</label>
                <input type="number" id="inp-int-port" class="input-control" placeholder="Ví dụ: 8080">
            </div>
            <div class="input-group">
                <label>Giao Thức</label>
                <select id="inp-proto" class="input-control">
                    <option value="TCP">TCP (Dành cho Web, Remote, SSH)</option>
                    <option value="UDP">UDP (Dành cho Game, Streaming)</option>
                </select>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
                <button class="btn btn-secondary" onclick="closeModal('modal-port')">Hủy</button>
                <button class="btn btn-primary" onclick="submitOpenPort()">Xác Nhận Mở Port</button>
            </div>
        </div>
    </div>

    <!-- Modal Mở Tường Lửa Windows (Inbound) -->
    <div class="modal" id="modal-fw">
        <div class="modal-box">
            <h3 style="font-size: 18px; margin-bottom: 16px;">🧱 Mở Luật Tường Lửa Windows (Inbound Rule)</h3>
            <div class="input-group">
                <label>Tên Luật (Rule Name)</label>
                <input type="text" id="inp-fw-name" class="input-control" placeholder="Ví dụ: MyWebServer">
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

    <script>
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

        async function fetchFWRules() {
            try {
                const res = await fetch('/api/fw/rules');
                const rules = await res.json();
                const tbody = document.getElementById('fw-tbody');
                if (!rules || rules.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Chưa có luật nào. Bấm "Mở Tường Lửa Windows" để thêm.</td></tr>';
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
            } catch(e) {
                console.error("Fetch FW error:", e);
            }
        }
        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                document.getElementById('system-info').innerText = `${data.net.hostname} - ${data.net.system} (Core i3 5th)`;
                document.getElementById('wan-ip').innerText = data.net.wan_ip;
                document.getElementById('lan-ip').innerText = data.net.lan_ip;
                document.getElementById('rd-status').innerText = data.rd_status;
                
                // Hardware
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
                
                document.getElementById('uptime').innerText = data.hw.uptime;
                document.getElementById('boot-time').innerText = `Khởi động: ${data.hw.boot_time}`;

                fetchPorts();
                fetchFWRules();
                fetchSnapshots();
            } catch (e) {
                console.error("Fetch status error:", e);
            }
        }

        async function fetchPorts() {
            try {
                const res = await fetch('/api/ports');
                const ports = await res.json();
                const tbody = document.getElementById('ports-tbody');
                if (!ports || ports.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Chưa có cổng nào mở qua UPnP. Bấm "+ Mở Port Mới" để mở cổng ngay.</td></tr>';
                    return;
                }
                tbody.innerHTML = ports.map(p => `
                    <tr>
                        <td><strong>${p.external_port || p.externalPort}</strong></td>
                        <td>${p.internal_port || p.internalPort || '-'}</td>
                        <td><span class="tag-${(p.protocol || 'TCP').toLowerCase()}">${p.protocol || 'TCP'}</span></td>
                        <td>${p.description || 'PcManager Service'}</td>
                        <td><button class="copy-btn" onclick="closePort(${p.external_port || p.externalPort}, '${p.protocol || 'TCP'}')">Đóng Cổng</button></td>
                    </tr>
                `).join('');
            } catch(e) {
                console.error("Fetch ports error:", e);
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
                    <div class="gallery-item">
                        <img src="/snapshots/${s.name}" alt="${s.name}">
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
        }

        async function closePort(port, proto) {
            if (!confirm(`Bạn có chắc muốn đóng port ${port} (${proto}) không?`)) return;
            const res = await fetch(`/api/ports/close?ext=${port}&proto=${proto}`, { method: 'POST' });
            const data = await res.json();
            alert(data.message);
            fetchPorts();
        }

        function copyText(elemId) {
            const text = document.getElementById(elemId).innerText;
            navigator.clipboard.writeText(text);
            alert("Đã sao chép: " + text);
        }

        function openModal(id) { document.getElementById(id).classList.add('active'); }
        function closeModal(id) { document.getElementById(id).classList.remove('active'); }

        // Initial load & Polling every 5s
        fetchStatus();
        setInterval(fetchStatus, 5000);
    </script>
</body>
</html>
"""

class DashboardRequestHandler(BaseHTTPRequestHandler):
    upnp_mgr = None

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
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

    def _send_json(self, data: dict | list):
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress standard HTTP request logging in stdout
        pass

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

def start_dashboard_server(upnp_mgr, port: int = DASHBOARD_PORT) -> threading.Thread:
    """Run Web Dashboard in a daemon background thread."""
    DashboardRequestHandler.upnp_mgr = upnp_mgr
    server = HTTPServer(("0.0.0.0", port), DashboardRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"🚀 PcManager Web Dashboard is running at http://localhost:{port}")
    return thread

