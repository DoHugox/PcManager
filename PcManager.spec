# -*- mode: python ; coding: utf-8 -*-
# PyInstaller Spec for PcManager (VNServerSentinel)
# Bundles entire agent into a single standalone Windows executable (.exe)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('bios_helper.ps1', '.'),
        ('VERSION', '.'),
        ('HUONG_DAN_CAI_DAT.md', '.'),
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'upnpy',
        'psutil',
        'PIL',
        'PIL.ImageGrab',
        'cv2',
        'requests',
        'dotenv',
        'win32api',
        'win32con',
        'win32gui',
        'win32ts',
        'config',
        'network_upnp',
        'security_guard',
        'system_monitor',
        'file_manager',
        'telegram_bot',
        'updater',
        'remote_desktop',
        'web_dashboard',
        'tray_icon',
        'pystray'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PcManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Runs silently in the background (No black CMD window)
    icon='assets/app.ico',
    uac_admin=True, # Auto-prompt Windows Administrator UAC privileges
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
