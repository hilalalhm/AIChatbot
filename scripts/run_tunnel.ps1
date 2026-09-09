$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $RepoRoot ".env"
$Cloudflared = Join-Path $env:LOCALAPPDATA "cloudflared\cloudflared.exe"
$LogOut = Join-Path $env:TEMP "cloudflared_aichatbot.out.log"
$LogErr = Join-Path $env:TEMP "cloudflared_aichatbot.err.log"

if (-not (Test-Path $Cloudflared)) {
    throw "cloudflared tidak ditemukan. Install dulu: winget install Cloudflare.cloudflared"
}

function Set-EnvValue($name, $value) {
    $content = Get-Content $EnvFile
    $found = $false
    for ($i = 0; $i -lt $content.Count; $i++) {
        if ($content[$i] -match "^$name=") {
            $content[$i] = "$name=$value"
            $found = $true
            break
        }
    }
    if ($found) {
        Set-Content -Path $EnvFile -Value $content -Encoding utf8
    } else {
        Add-Content -Path $EnvFile -Value "$name=$value" -Encoding utf8
    }
    Write-Host "[.env] $name diupdate"
}

$secret = ""
$line = (Get-Content $EnvFile | Where-Object { $_ -match "^TELEGRAM_WEBHOOK_SECRET=" })
if ($line) {
    $secret = ($line[0] -replace "^TELEGRAM_WEBHOOK_SECRET=", "").Trim('"')
}
if ([string]::IsNullOrEmpty($secret)) {
    $secret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    Set-EnvValue "TELEGRAM_WEBHOOK_SECRET" $secret
}

Get-Process -Name cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
Remove-Item $LogOut, $LogErr -ErrorAction SilentlyContinue

Write-Host "[tunnel] Menjalankan cloudflared quick tunnel ke http://127.0.0.1:8000 ..."
$proc = Start-Process -FilePath $Cloudflared -ArgumentList "tunnel", "--url", "http://127.0.0.1:8000", "--no-autoupdate" -RedirectStandardOutput $LogOut -RedirectStandardError $LogErr -PassThru -WindowStyle Hidden

$url = $null
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    $log = ""
    if (Test-Path $LogOut) { $log += Get-Content $LogOut -Raw -ErrorAction SilentlyContinue }
    if (Test-Path $LogErr) { $log += Get-Content $LogErr -Raw -ErrorAction SilentlyContinue }
    if ($log -match "https://[a-zA-Z0-9-]+\.trycloudflare\.com") {
        $url = $Matches[0]
        break
    }
    if ($proc.HasExited) { break }
}

if (-not $url) {
    Write-Host "[tunnel] GAGAL mendapatkan URL tunnel."
    $log = ""
    if (Test-Path $LogOut) { $log += Get-Content $LogOut -Raw -ErrorAction SilentlyContinue }
    if (Test-Path $LogErr) { $log += Get-Content $LogErr -Raw -ErrorAction SilentlyContinue }
    Write-Host $log
    exit 1
}

Write-Host "[tunnel] URL publik: $url"
Set-EnvValue "TELEGRAM_WEBHOOK_URL" "$url/telegram/webhook"

Write-Host "[webhook] Mendaftarkan webhook ke Telegram ..."
Push-Location $RepoRoot
try {
    $env:PYTHONPATH = $RepoRoot
    & ".venv\Scripts\python.exe" "scripts\setup_webhook.py"
} finally {
    Pop-Location
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "[webhook] GAGAL mendaftarkan webhook."
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host ""
Write-Host "======================================================"
Write-Host "  Tunnel AKTIF (jangan tutup terminal ini)."
Write-Host "  Kirim pesan ke @AiChat258_Bot untuk mencoba."
Write-Host "  Webhook: $url/telegram/webhook"
Write-Host "======================================================"