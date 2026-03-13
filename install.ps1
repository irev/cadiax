Param(
    [switch]$InstallNode,
    [switch]$SkipSetup,
    [string]$PythonCommand = "python",
    [string]$VenvPath = ".venv",
    [switch]$ReuseVenv,
    [switch]$SkipUserShim
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

function Show-NextSteps {
    Param(
        [string]$VenvPath,
        [string]$VenvPython,
        [hashtable]$ShimInfo = $null
    )

    $VenvCadiax = Join-Path $PWD "$VenvPath\\Scripts\\cadiax.exe"
    $ResolvedCadiax = Get-Command "cadiax" -ErrorAction SilentlyContinue
    $LayoutInfo = & $VenvPython -c "from cadiax.core.path_layout import get_config_env_file, get_state_dir, get_workspace_root; print(get_config_env_file()); print(get_state_dir()); print(get_workspace_root())"
    $ConfigPath = ""
    $StatePath = ""
    $WorkspacePath = ""
    if ($LayoutInfo.Count -ge 3) {
        $ConfigPath = $LayoutInfo[0]
        $StatePath = $LayoutInfo[1]
        $WorkspacePath = $LayoutInfo[2]
    }

    Write-Host ""
    Write-Host "Cadiax installed"
    Write-Host "CLI: $VenvPath\\Scripts\\cadiax.exe"
    Write-Host "Telegram CLI: $VenvPath\\Scripts\\cadiax-telegram.exe"
    if ($ConfigPath) {
        Write-Host "Config: $ConfigPath"
        Write-Host "State: $StatePath"
        Write-Host "Workspace: $WorkspacePath"
    }
    Write-Host ""
    Write-Host "Gunakan salah satu cara berikut:"
    Write-Host "1. Langsung jalankan: $VenvPath\\Scripts\\cadiax.exe"
    Write-Host "2. Aktifkan virtual environment terlebih dulu:"
    Write-Host "   .\\$VenvPath\\Scripts\\Activate.ps1"
    Write-Host "   cadiax"

    $AcceptedPaths = @($VenvCadiax)
    if ($ShimInfo) {
        $AcceptedPaths += $ShimInfo.cadiax_cmd
    }

    if ($ResolvedCadiax -and ($AcceptedPaths -notcontains $ResolvedCadiax.Path)) {
        Write-Host ""
        Write-Warning "Command `cadiax` pada shell ini masih mengarah ke: $($ResolvedCadiax.Path)"
        Write-Host "Itu bukan executable project ini. Aktifkan virtual environment atau gunakan path CLI di atas."
    }
}

function Register-UserCommandShims {
    Param(
        [string]$ProjectRoot,
        [string]$VenvPath
    )

    $ShimDir = Join-Path $HOME ".cadiax\\bin"
    New-Item -ItemType Directory -Force -Path $ShimDir | Out-Null

    $CadiaxExe = Join-Path $ProjectRoot "$VenvPath\\Scripts\\cadiax.exe"
    $TelegramExe = Join-Path $ProjectRoot "$VenvPath\\Scripts\\cadiax-telegram.exe"
    $CadiaxCmd = "@echo off`r`n""$CadiaxExe"" %*`r`n"
    $TelegramCmd = "@echo off`r`n""$TelegramExe"" %*`r`n"

    Set-Content -Path (Join-Path $ShimDir "cadiax.cmd") -Value $CadiaxCmd -Encoding ascii
    Set-Content -Path (Join-Path $ShimDir "cadiax-telegram.cmd") -Value $TelegramCmd -Encoding ascii

    $CurrentUserPath = [Environment]::GetEnvironmentVariable("Path", "User") ?? ""
    $Parts = @($CurrentUserPath -split ";" | Where-Object { $_.Trim() -ne "" })
    $NormalizedShimDir = [System.IO.Path]::GetFullPath($ShimDir)
    $Filtered = @($Parts | Where-Object { [System.IO.Path]::GetFullPath($_) -ne $NormalizedShimDir })
    $NewUserPath = ($NormalizedShimDir + ($(if ($Filtered.Count -gt 0) { ";" + ($Filtered -join ";") } else { "" })))
    [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
    $env:Path = "$NormalizedShimDir;$env:Path"

    return @{
        shim_dir = $NormalizedShimDir
        cadiax_cmd = (Join-Path $ShimDir "cadiax.cmd")
        telegram_cmd = (Join-Path $ShimDir "cadiax-telegram.cmd")
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

if ((Test-Path $VenvPath) -and (-not $ReuseVenv)) {
    Write-Step "Menghapus virtual environment lama di $VenvPath"
    Remove-Item -Recurse -Force $VenvPath
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

$ShimInfo = $null
if (-not $SkipUserShim) {
    Write-Step "Mendaftarkan command Cadiax ke user PATH"
    $ShimInfo = Register-UserCommandShims -ProjectRoot $PWD -VenvPath $VenvPath
}

if ($InstallNode) {
    Write-Step "Menyiapkan dashboard dependency"
    Invoke-CheckedCommand -Label "cadiax dashboard install" -Command @($VenvPython, "-m", "cadiax.cli", "dashboard", "install")
}

if (-not $SkipSetup) {
    Write-Step "Menjalankan Cadiax setup"
    Invoke-CheckedCommand -Label "cadiax setup" -Command @($VenvPython, "-m", "cadiax.cli", "setup")
}

Show-NextSteps -VenvPath $VenvPath -VenvPython $VenvPython -ShimInfo $ShimInfo
if ($ShimInfo) {
    Write-Host ""
    Write-Host "User command shims:"
    Write-Host "- cadiax: $($ShimInfo.cadiax_cmd)"
    Write-Host "- cadiax-telegram: $($ShimInfo.telegram_cmd)"
    Write-Host "- user PATH updated: $($ShimInfo.shim_dir)"
    Write-Host "Buka shell baru agar command `cadiax` memakai shim Cadiax yang baru."
}
