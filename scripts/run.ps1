$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\pythonw.exe"

if (-not (Test-Path $VenvPython)) {
    throw "尚未安装项目环境。请先运行 scripts\setup.ps1。"
}

Start-Process -FilePath $VenvPython -ArgumentList "-m", "ns2pro_bridge" -WorkingDirectory $ProjectRoot

