param(
    [Parameter(Mandatory = $true)]
    [string]$PythonPath
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WorkRoot = Join-Path $ProjectRoot "build\third-party\vgamepad-0.1.0"
$ArchivePath = Join-Path $WorkRoot "vgamepad-0.1.0.tar.gz"
$ExtractRoot = Join-Path $WorkRoot "source"
$WheelRoot = Join-Path $WorkRoot "wheel"
$SourceUrl = "https://files.pythonhosted.org/packages/8a/54/0eaddc33f84247963af078f364b37153d09fcd6cdc398f243ec3e8842c56/vgamepad-0.1.0.tar.gz"
$ExpectedSha256 = "57F6BD01AEC0C172947517FB782D150EF9B285F7F4D524C317374FA5C24A89DE"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "找不到 Python：$PythonPath"
}

New-Item -ItemType Directory -Path $WorkRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $ArchivePath)) {
    Invoke-WebRequest -Uri $SourceUrl -OutFile $ArchivePath
}
$ActualSha256 = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash
if ($ActualSha256 -ne $ExpectedSha256) {
    throw "vgamepad 源码归档哈希不匹配：$ActualSha256"
}

$ResolvedWorkRoot = [System.IO.Path]::GetFullPath($WorkRoot)
foreach ($Target in @($ExtractRoot, $WheelRoot)) {
    $ResolvedTarget = [System.IO.Path]::GetFullPath($Target)
    if (-not $ResolvedTarget.StartsWith(
        $ResolvedWorkRoot + [System.IO.Path]::DirectorySeparatorChar,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "拒绝清理工作目录外的路径：$ResolvedTarget"
    }
    if (Test-Path -LiteralPath $ResolvedTarget) {
        Remove-Item -LiteralPath $ResolvedTarget -Recurse -Force
    }
    New-Item -ItemType Directory -Path $ResolvedTarget -Force | Out-Null
}

& tar.exe -xzf $ArchivePath -C $ExtractRoot
if ($LASTEXITCODE -ne 0) {
    throw "无法解压 vgamepad 源码归档。"
}
$SourceRoot = Join-Path $ExtractRoot "vgamepad-0.1.0"
$SetupPath = Join-Path $SourceRoot "setup.py"
if (-not (Test-Path -LiteralPath $SetupPath)) {
    throw "vgamepad 源码归档缺少 setup.py。"
}

# PyPI 的 v0.1.0 sdist 会在构建 wheel 时同步启动旧版 ViGEmBus MSI。
# 此补丁只禁用该副作用；vgamepad Python 代码和 ViGEmClient DLL 保持原样。
$InstallerCall = "            subprocess.call(['msiexec', '/i', '%s' % str(pathMsi)], shell=True)"
$Replacement = "            warnings.warn('Automatic ViGEmBus installation disabled; install the driver separately.')"
$SetupText = Get-Content -LiteralPath $SetupPath -Raw
$FirstMatch = $SetupText.IndexOf($InstallerCall, [System.StringComparison]::Ordinal)
$LastMatch = $SetupText.LastIndexOf($InstallerCall, [System.StringComparison]::Ordinal)
if ($FirstMatch -lt 0 -or $FirstMatch -ne $LastMatch) {
    throw "vgamepad setup.py 与已审计的 v0.1.0 内容不一致，拒绝打补丁。"
}
$SetupText = $SetupText.Replace($InstallerCall, $Replacement)
Set-Content -LiteralPath $SetupPath -Value $SetupText -Encoding UTF8 -NoNewline

& $PythonPath -m pip wheel $SourceRoot --no-deps --wheel-dir $WheelRoot
if ($LASTEXITCODE -ne 0) {
    throw "vgamepad wheel 构建失败。"
}
$Wheels = @(Get-ChildItem -LiteralPath $WheelRoot -Filter "vgamepad-0.1.0-*.whl" -File)
if ($Wheels.Count -ne 1) {
    throw "预期生成一个 vgamepad wheel，实际为 $($Wheels.Count) 个。"
}
& $PythonPath -m pip install --force-reinstall $Wheels[0].FullName
if ($LASTEXITCODE -ne 0) {
    throw "vgamepad wheel 安装失败。"
}

Write-Host "已从固定哈希的 vgamepad 0.1.0 源码构建并安装；未运行驱动 MSI。"
