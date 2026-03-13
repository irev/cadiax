Param(
    [switch]$InstallNode,
    [switch]$SkipSetup,
    [string]$PythonCommand = "python",
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    Param([string]$Message)
    Write-Host "[Cadiax] $Message"
}

function Test-Command {
    Param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Ensure-WingetPackage {
    Param(
        [string]$Id,
        [string]$Label
    )

    if (-not (Test-Command "winget")) {
        throw "winget tidak tersedia. Install $Label secara manual lalu jalankan script ini lagi."
    }

    Write-Step "Menginstall $Label via winget..."
    winget install --id $Id --exact --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Gagal menginstall $Label via winget."
    }
}

function Invoke-CheckedCommand {
    Param(
        [string]$Label,
        [string[]]$Command
    )

    & $Command[0] $Command[1..($Command.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "Langkah gagal: $Label"
    }
}

if (-not (Test-Command $PythonCommand)) {
    Ensure-WingetPackage -Id "Python.Python.3.12" -Label "Python"
}

if (-not (Test-Command "git")) {
    Ensure-WingetPackage -Id "Git.Git" -Label "Git"
}

if ($InstallNode -and -not (Test-Command "node")) {
    Ensure-WingetPackage -Id "OpenJS.NodeJS.LTS" -Label "Node.js LTS"
}

Write-Step "Menyiapkan virtual environment $VenvPath"
Invoke-CheckedCommand -Label "python -m venv" -Command @($PythonCommand, "-m", "venv", $VenvPath)

$VenvPython = Join-Path $PWD "$VenvPath\\Scripts\\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment gagal dibuat."
}

Write-Step "Menyiapkan pip"
Invoke-CheckedCommand -Label "ensurepip" -Command @($VenvPython, "-m", "ensurepip", "--upgrade")

Write-Step "Mengupgrade pip"
Invoke-CheckedCommand -Label "pip install --upgrade pip" -Command @($VenvPython, "-m", "pip", "install", "--upgrade", "pip")

Write-Step "Menginstall Cadiax"
Invoke-CheckedCommand -Label "pip install ." -Command @($VenvPython, "-m", "pip", "install", ".")

Write-Step "Menyiapkan dokumen workspace aktif"
Invoke-CheckedCommand -Label "cadiax bootstrap foundation" -Command @($VenvPython, "-m", "cadiax.cli", "bootstrap", "foundation")

if ($InstallNode) {
    Write-Step "Menyiapkan dashboard dependency"
    Invoke-CheckedCommand -Label "cadiax dashboard install" -Command @($VenvPython, "-m", "cadiax.cli", "dashboard", "install")
}

if (-not $SkipSetup) {
    Write-Step "Menjalankan Cadiax setup"
    Invoke-CheckedCommand -Label "cadiax setup" -Command @($VenvPython, "-m", "cadiax.cli", "setup")
}

Write-Host ""
Write-Host "Cadiax installed"
Write-Host "CLI: $VenvPath\\Scripts\\cadiax.exe"
Write-Host "Telegram CLI: $VenvPath\\Scripts\\cadiax-telegram.exe"
