<#
.SYNOPSIS
    VNServerSentinel - Remote BIOS Power-Loss Auto Configuration Helper
.DESCRIPTION
    Tự động cấu hình tính năng "Tự động bật nguồn khi có điện lại" (AC Power Recovery)
    từ xa ngay trong Windows mà không cần vào BIOS thủ công.
    Hỗ trợ các hãng phổ biến: Dell, HP, Lenovo và bo mạch chủ hỗ trợ WMI.
    Yêu cầu: Chạy với quyền Administrator.
#>

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   VNServerSentinel - Cấu hình Tự Bật Nguồn Khi Có Điện (BIOS) " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# Kiểm tra quyền Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[!] LỖI: Script này bắt buộc phải chạy dưới quyền Administrator!" -ForegroundColor Red
    Write-Host "    Vui lòng chuột phải vào PowerShell chọn 'Run as Administrator'." -ForegroundColor Yellow
    exit 1
}

# Lấy thông tin nhà sản xuất máy tính
$sysInfo = Get-CimInstance Win32_ComputerSystem
$manufacturer = $sysInfo.Manufacturer
$model = $sysInfo.Model

Write-Host "[+] Thiết bị phát hiện: $manufacturer - $model" -ForegroundColor Green

# 1. Nếu là máy DELL
if ($manufacturer -match "Dell") {
    Write-Host "[*] Phát hiện phần cứng DELL. Đang kiểm tra công cụ Dell Command | Configure..." -ForegroundColor Yellow
    $cctkPath = "C:\Program Files (x86)\Dell\Command Configure\X86_64\cctk.exe"
    if (Test-Path $cctkPath) {
        & $cctkPath --acpower=on
        Write-Host "[OK] Đã cấu hình DELL AC Power Recovery: ON thành công!" -ForegroundColor Green
    } else {
        Write-Host "[!] Chưa cài đặt Dell Command Configure. Bạn có thể tải tại:" -ForegroundColor Yellow
        Write-Host "    https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=c2w3r"
    }
}
# 2. Nếu là máy HP
elseif ($manufacturer -match "HP|Hewlett-Packard") {
    Write-Host "[*] Phát hiện phần cứng HP. Đang kiểm tra HP BiosConfigUtility..." -ForegroundColor Yellow
    $bcuPath = "C:\Program Files\HP\BIOS Configuration Utility\BiosConfigUtility64.exe"
    if (Test-Path $bcuPath) {
        & $bcuPath /SetConfigValue:"After Power Loss","Power On"
        Write-Host "[OK] Đã cấu hình HP After Power Loss: Power On thành công!" -ForegroundColor Green
    } else {
        Write-Host "[!] Chưa cài đặt HP BCU. Có thể tải tại: https://ftp.hp.com/pub/caps-softpaq/cmit/HP_BCU.html" -ForegroundColor Yellow
    }
}
# 3. Nếu là máy LENOVO
elseif ($manufacturer -match "Lenovo") {
    Write-Host "[*] Phát hiện phần cứng LENOVO. Đang cấu hình qua WMI..." -ForegroundColor Yellow
    try {
        (Get-WmiObject -Namespace root\wmi -Class Lenovo_SetBiosSetting).SetBiosSetting("After Power Loss,Power On")
        (Get-WmiObject -Namespace root\wmi -Class Lenovo_SaveBiosSettings).SaveBiosSettings()
        Write-Host "[OK] Đã cấu hình LENOVO After Power Loss: Power On qua WMI thành công!" -ForegroundColor Green
    } catch {
        Write-Host "[!] Lỗi cấu hình qua WMI Lenovo: $_" -ForegroundColor Red
    }
}
# 4. Các bo mạch chủ khác (WMI / Generic)
else {
    Write-Host "[*] Bo mạch chủ khác ($manufacturer). Kiểm tra thiết lập WMI..." -ForegroundColor Yellow
    Write-Host "[i] Nếu bo mạch chủ là ASUS / Gigabyte / ASRock tự ráp:" -ForegroundColor Cyan
    Write-Host "    Hãy vào BIOS -> Tab 'Advanced' hoặc 'Power Management' -> Tìm 'Restore on AC Power Loss' và chọn 'Power On'." -ForegroundColor White
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Hoàn tất kiểm tra!" -ForegroundColor Green
