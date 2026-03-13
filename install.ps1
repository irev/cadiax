Param(
    [switch]$InstallNode,
    [switch]$SkipSetup,
    [string]$PythonCommand = "python"
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

Write-Step "Menyiapkan virtual environment .venv"
& $PythonCommand -m venv .venv

$VenvPython = Join-Path $PWD ".venv\\Scripts\\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment gagal dibuat."
}

Write-Step "Mengupgrade pip"
& $VenvPython -m pip install --upgrade pip

Write-Step "Menginstall Cadiax"
& $VenvPython -m pip install .

if ($InstallNode) {
    Write-Step "Menyiapkan dashboard dependency"
    & $VenvPython -m cadiax.cli dashboard install
}

if (-not $SkipSetup) {
    Write-Step "Menjalankan Cadiax setup"
    & $VenvPython -m cadiax.cli setup
}

Write-Host ""
Write-Host "Cadiax installed"
Write-Host "CLI: .venv\\Scripts\\cadiax.exe"
Write-Host "Telegram CLI: .venv\\Scripts\\cadiax-telegram.exe"
