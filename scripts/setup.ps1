$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    python -m venv (Join-Path $ProjectRoot ".venv")
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e "$ProjectRoot[dev]"

Write-Host ""
Write-Host "Python 环境安装完成。"
Write-Host "还需要 ViGEmBus 1.22.0 驱动："
Write-Host "https://github.com/nefarius/ViGEmBus/releases/tag/v1.22.0"
Write-Host "安装驱动并重启电脑后，运行 scripts\run.ps1。"

