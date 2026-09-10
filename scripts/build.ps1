param([string]$DistPath = "")

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Version = & $VenvPython -c "import sys; sys.path.insert(0, 'src'); import ns2pro_bridge; print(ns2pro_bridge.__version__)"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Version)) {
    throw "无法读取项目版本号。"
}
$Version = $Version.Trim()
$ExeName = "NS2ProBridge-v$Version"
$EffectiveDistPath = if ([string]::IsNullOrWhiteSpace($DistPath)) { "dist\v$Version" } else { $DistPath }
$ResolvedDistPath = if ([System.IO.Path]::IsPathRooted($EffectiveDistPath)) {
    $EffectiveDistPath
} else {
    Join-Path $ProjectRoot $EffectiveDistPath
}

if (-not (Test-Path $VenvPython)) {
    throw "尚未安装项目环境。请先运行 scripts\setup.ps1。"
}

Push-Location $ProjectRoot
try {
    $VersionParts = $Version.Split('.')
    if ($VersionParts.Count -ne 3) {
        throw "版本号必须采用 MAJOR.MINOR.PATCH 格式，当前为：$Version"
    }
    $VersionInfoPath = Join-Path $ProjectRoot "build\windows-version-info.txt"
    New-Item -ItemType Directory -Path (Split-Path $VersionInfoPath) -Force | Out-Null
    $VersionInfo = @"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($($VersionParts[0]), $($VersionParts[1]), $($VersionParts[2]), 0), prodvers=($($VersionParts[0]), $($VersionParts[1]), $($VersionParts[2]), 0), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'NS2 Pro Bridge contributors'),
    StringStruct('FileDescription', 'NS2 Pro Wireless Bridge'),
    StringStruct('FileVersion', '$Version'),
    StringStruct('InternalName', '$ExeName'),
    StringStruct('LegalCopyright', 'MIT License'),
    StringStruct('OriginalFilename', '$ExeName.exe'),
    StringStruct('ProductName', 'NS2 Pro Wireless Bridge'),
    StringStruct('ProductVersion', '$Version')
  ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
"@
    Set-Content -LiteralPath $VersionInfoPath -Value $VersionInfo -Encoding UTF8
    $PyInstallerArgs = @(
        "--noconfirm"
        "--clean"
        "--onefile"
        "--noconsole"
        "--name", $ExeName
        "--distpath", $ResolvedDistPath
        "--version-file", $VersionInfoPath
        "--collect-all", "bleak"
        "--collect-all", "vgamepad"
        "--paths", "src"
    )
    $ViiperRuntime = Join-Path $ProjectRoot "runtime\viiper-haptic.exe"
    $ViiperLicense = Join-Path $ProjectRoot "runtime\VIIPER_LICENSE.txt"
    if ((Test-Path $ViiperRuntime) -and (Test-Path $ViiperLicense)) {
        $PyInstallerArgs += @(
            "--add-binary", "$ViiperRuntime;runtime"
            "--add-data", "$ViiperLicense;runtime"
        )
        Write-Host "将 VIIPER Haptic v0.8.0 作为可选 GPL 运行时嵌入。"
    }
    else {
        Write-Warning "未找到完整 VIIPER 运行时；Nintendo 虚拟设备模式不会内置。"
    }
    $PyInstallerArgs += "src\ns2pro_bridge_launcher.py"

    & $VenvPython -m PyInstaller @PyInstallerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller 构建失败，退出码：$LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

$ReleaseDocuments = @(
    "LICENSE",
    "README.md",
    "COMPATIBILITY.md",
    "LEGAL.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md"
)
foreach ($Document in $ReleaseDocuments) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot $Document) `
        -Destination (Join-Path $ResolvedDistPath $Document) -Force
}
Copy-Item -LiteralPath (Join-Path $ProjectRoot "runtime\VIIPER_LICENSE.txt") `
    -Destination (Join-Path $ResolvedDistPath "VIIPER_LICENSE.txt") -Force
$LicenseSource = Join-Path $ProjectRoot "third_party\licenses"
$LicenseDestination = Join-Path $ResolvedDistPath "licenses"
if (Test-Path -LiteralPath $LicenseSource) {
    New-Item -ItemType Directory -Path $LicenseDestination -Force | Out-Null
    foreach ($LicenseFile in Get-ChildItem -LiteralPath $LicenseSource -File) {
        Copy-Item -LiteralPath $LicenseFile.FullName -Destination $LicenseDestination -Force
    }
}
$CorrespondingSource = Join-Path $ProjectRoot `
    "third_party\source\XinHeLianSheng-Pro2-Bridge-b274daa-source.zip"
if (Test-Path -LiteralPath $CorrespondingSource) {
    Copy-Item -LiteralPath $CorrespondingSource -Destination $ResolvedDistPath -Force
}
$PackagePath = Join-Path $ResolvedDistPath "$ExeName-Windows-x64.zip"
$PackageInputs = @(
    (Join-Path $ResolvedDistPath "$ExeName.exe"),
    (Join-Path $ResolvedDistPath "VIIPER_LICENSE.txt")
)
$PackageInputs += $ReleaseDocuments | ForEach-Object {
    Join-Path $ResolvedDistPath $_
}
if (Test-Path -LiteralPath $LicenseDestination) {
    $PackageInputs += $LicenseDestination
}
Compress-Archive -LiteralPath $PackageInputs -DestinationPath $PackagePath -Force
Write-Host "构建完成：$(Join-Path $ResolvedDistPath "$ExeName.exe")"
