Param(
    [ValidateSet("install", "reinstall", "uninstall")]
    [string]$Mode = "install",
    [switch]$InstallNode,
    [switch]$SkipSetup,
    [string]$PythonCommand = "python",
    [string]$AppRoot = "",
    [string]$VenvPath = "",
    [switch]$ReuseVenv,
    [switch]$SkipUserShim,
    [switch]$SkipPowerShellProfileShim,
    [switch]$PurgeData
)

$ErrorActionPreference = "Stop"

function Write-Step {
    Param([string]$Message)
    Write-Host "[Cadiax] $Message"
}

function Get-DefaultAppRoot {
    if ($env:LOCALAPPDATA) {
        return Join-Path $env:LOCALAPPDATA "Cadiax\\app"
    }
    return Join-Path $HOME "AppData\\Local\\Cadiax\\app"
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

function Test-PythonMinimumVersion {
    Param([string]$Command)

    try {
        $VersionText = & $Command -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
    } catch {
        return $false
    }
    if (-not $VersionText) {
        return $false
    }
    try {
        $Version = [Version]$VersionText.Trim()
    } catch {
        return $false
    }
    return $Version -ge [Version]"3.10.0"
}

function Test-PythonVenvSupport {
    Param([string]$Command)

    $ProbeDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cadiax-venv-" + [guid]::NewGuid().ToString("N"))
    try {
        & $Command -m venv $ProbeDir *> $null
        return ($LASTEXITCODE -eq 0) -and (Test-Path (Join-Path $ProbeDir "Scripts\\python.exe"))
    } catch {
        return $false
    } finally {
        if (Test-Path $ProbeDir) {
            Remove-Item -Recurse -Force $ProbeDir -ErrorAction SilentlyContinue
        }
    }
}

function Ensure-PythonReady {
    Param([string]$Command)

    if (-not (Test-Command $Command)) {
        Ensure-WingetPackage -Id "Python.Python.3.12" -Label "Python"
        if (-not (Test-Command $Command)) {
            throw "Python berhasil diinstall tetapi command '$Command' belum tersedia di shell ini. Buka shell baru atau gunakan -PythonCommand dengan path interpreter yang benar."
        }
    }

    if (-not (Test-PythonMinimumVersion $Command)) {
        throw "Cadiax membutuhkan Python >= 3.10. Command '$Command' pada sistem ini tidak memenuhi syarat. Gunakan interpreter yang lebih baru atau jalankan installer ulang setelah update Python."
    }

    if (-not (Test-PythonVenvSupport $Command)) {
        throw "Python tersedia tetapi modul venv/ensurepip tidak siap. Perbaiki instalasi Python atau pasang distribusi Python yang menyertakan virtual environment support."
    }
}

function Show-PreflightSummary {
    Param(
        [string]$PythonCommand,
        [bool]$InstallNodeRequested
    )

    Write-Step "Preflight dependency check"
    Write-Host "- python command: $PythonCommand"
    Write-Host "- python ready: yes"
    Write-Host "- git ready: $(if (Test-Command 'git') { 'yes' } else { 'no' })"
    if ($InstallNodeRequested) {
        Write-Host "- node requested: yes"
        Write-Host "- node ready: $(if (Test-Command 'node') { 'yes' } else { 'no' })"
    } else {
        Write-Host "- node requested: no"
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

function Reset-VenvDirectory {
    Param([string]$TargetPath)

    if (-not (Test-Path $TargetPath)) {
        return
    }

    Write-Step "Menghapus virtual environment lama di $TargetPath"
    try {
        Remove-Item -Recurse -Force $TargetPath -ErrorAction Stop
        return
    } catch {
        throw "Virtual environment lama sedang dipakai proses lain. Tutup shell, service, atau proses Cadiax yang masih aktif lalu jalankan installer lagi. Jika memang ingin mempertahankan venv yang sama, gunakan -ReuseVenv."
    }
}

function Remove-UserCommandShims {
    $ShimDir = Join-Path $HOME ".cadiax\bin"
    foreach ($ShimName in @("cadiax.cmd", "cadiax-telegram.cmd")) {
        $ShimPath = Join-Path $ShimDir $ShimName
        if (Test-Path $ShimPath) {
            Remove-Item -Force $ShimPath -ErrorAction SilentlyContinue
        }
    }
    return $ShimDir
}

function Remove-PowerShellProfileShims {
    $MarkerStart = "# >>> Cadiax profile shim >>>"
    $MarkerEnd = "# <<< Cadiax profile shim <<<"
    $Pattern = [regex]::Escape($MarkerStart) + ".*?" + [regex]::Escape($MarkerEnd) + "(\r?\n)?"
    $DocumentsRoot = [Environment]::GetFolderPath("MyDocuments")
    $ProfilePaths = @(
        $PROFILE.CurrentUserAllHosts,
        (Join-Path $DocumentsRoot "PowerShell\profile.ps1"),
        (Join-Path $DocumentsRoot "PowerShell\Microsoft.PowerShell_profile.ps1"),
        (Join-Path $DocumentsRoot "WindowsPowerShell\profile.ps1"),
        (Join-Path $DocumentsRoot "WindowsPowerShell\Microsoft.PowerShell_profile.ps1")
    ) | Select-Object -Unique

    foreach ($ProfilePath in $ProfilePaths) {
        if (-not (Test-Path $ProfilePath)) {
            continue
        }
        $Current = Get-Content $ProfilePath -Raw -ErrorAction SilentlyContinue
        if (-not $Current -or $Current -notmatch [regex]::Escape($MarkerStart)) {
            continue
        }
        $Updated = [System.Text.RegularExpressions.Regex]::Replace(
            $Current,
            $Pattern,
            "",
            [System.Text.RegularExpressions.RegexOptions]::Singleline
        )
        Set-Content -Path $ProfilePath -Value $Updated -Encoding utf8
    }
}

function Invoke-Uninstall {
    Param(
        [string]$AppRoot,
        [switch]$PurgeData
    )

    $ConfigPath = [System.IO.Path]::GetFullPath((Join-Path ([Environment]::GetFolderPath("ApplicationData")) "Cadiax\config.env"))
    $ConfigDir = Split-Path -Parent $ConfigPath
    $StateDir = [System.IO.Path]::GetFullPath((Join-Path ([Environment]::GetFolderPath("LocalApplicationData")) "Cadiax\state"))
    $WorkspaceDir = [System.IO.Path]::GetFullPath((Join-Path $HOME "Cadiax\workspace"))

    Write-Step "Menjalankan uninstall Cadiax"
    if (Test-Path $AppRoot) {
        Remove-Item -Recurse -Force $AppRoot -ErrorAction Stop
        Write-Host "- app removed: $AppRoot"
    } else {
        Write-Host "- app removed: already-absent"
    }
    $ShimDir = Remove-UserCommandShims
    Remove-PowerShellProfileShims
    Write-Host "- user shims removed: $ShimDir"

    if ($PurgeData) {
        foreach ($PathItem in @($ConfigDir, $StateDir, $WorkspaceDir)) {
            if (Test-Path $PathItem) {
                Remove-Item -Recurse -Force $PathItem -ErrorAction SilentlyContinue
            }
        }
        Write-Host "- config/state/workspace purged: yes"
    } else {
        Write-Host "- config kept: $ConfigPath"
        Write-Host "- state kept: $StateDir"
        Write-Host "- workspace kept: $WorkspaceDir"
    }

    Write-Host ""
    Write-Host "Cadiax uninstalled"
}

function Show-NextSteps {
    Param(
        [string]$VenvPath,
        [string]$VenvPython,
        [string]$AppRoot,
        [hashtable]$ShimInfo = $null,
        [hashtable]$ProfileInfo = $null
    )

    $VenvCadiax = Join-Path $VenvPath "Scripts\\cadiax.exe"
    $ResolvedCadiax = Get-Command "cadiax" -ErrorAction SilentlyContinue
    $LayoutInfo = & $VenvPython -c "from cadiax.core.path_layout import get_config_env_file, get_state_dir, get_workspace_root, get_dashboard_root; print(get_config_env_file()); print(get_state_dir()); print(get_workspace_root()); print(get_dashboard_root())"
    $ConfigPath = ""
    $StatePath = ""
    $WorkspacePath = ""
    $DashboardPath = ""
    if ($LayoutInfo.Count -ge 4) {
        $ConfigPath = $LayoutInfo[0]
        $StatePath = $LayoutInfo[1]
        $WorkspacePath = $LayoutInfo[2]
        $DashboardPath = $LayoutInfo[3]
    }

    Write-Host ""
    Write-Host "Cadiax installed"
    Write-Host "App root: $AppRoot"
    Write-Host "CLI: $(Join-Path $VenvPath 'Scripts\\cadiax.exe')"
    Write-Host "Telegram CLI: $(Join-Path $VenvPath 'Scripts\\cadiax-telegram.exe')"
    if ($ConfigPath) {
        Write-Host "Config: $ConfigPath"
        Write-Host "State: $StatePath"
        Write-Host "Workspace: $WorkspacePath"
        Write-Host "Dashboard: $DashboardPath"
    }
    Write-Host ""
    Write-Host "Gunakan salah satu cara berikut:"
    Write-Host "1. Langsung jalankan: $(Join-Path $VenvPath 'Scripts\\cadiax.exe')"
    Write-Host "2. Aktifkan virtual environment terlebih dulu:"
    Write-Host "   $(Join-Path $VenvPath 'Scripts\\Activate.ps1')"
    Write-Host "   cadiax"

    $AcceptedPaths = @([System.IO.Path]::GetFullPath($VenvCadiax))
    if ($ShimInfo) {
        $AcceptedPaths += @($ShimInfo.cadiax_cmds | ForEach-Object { [System.IO.Path]::GetFullPath($_) })
    }
    $ResolvedCadiaxPath = if ($ResolvedCadiax) { [System.IO.Path]::GetFullPath($ResolvedCadiax.Path) } else { "" }

    if ($ResolvedCadiax -and ($AcceptedPaths -notcontains $ResolvedCadiaxPath)) {
        Write-Host ""
        Write-Warning "Command `cadiax` pada shell ini masih mengarah ke: $($ResolvedCadiax.Path)"
        if ($ResolvedCadiaxPath -like "*\\.pyenv\\*") {
            Write-Host "Konflik ini berasal dari pyenv/global Python lama. Command `cadiax` bawaan Cadiax tidak akan menang jika pyenv berada lebih dulu di PATH sistem."
            Write-Host "Remedi terbaik:"
            Write-Host "1. Buka shell baru PowerShell agar profile shim Cadiax aktif."
            Write-Host "2. Jika masih bentrok, uninstall package lama dari pyenv:"
            Write-Host "   pyenv which python"
            Write-Host "   <python> -m pip uninstall -y cadiax autonomiq otonomassist"
            Write-Host "   pyenv rehash"
        } else {
            Write-Host "Aktifkan virtual environment, gunakan shim Cadiax, atau buka shell baru setelah install."
        }
    }

    if ($ProfileInfo) {
        Write-Host ""
        Write-Host "PowerShell profile shims:"
        foreach ($ProfileEntry in $ProfileInfo.profiles) {
            Write-Host "- profile: $($ProfileEntry.path)"
            Write-Host "  status: $(if ($ProfileEntry.updated) { 'updated' } else { 'already-present' })"
        }
        Write-Host "Buka PowerShell baru agar command `cadiax` di PowerShell memakai shim Cadiax ini."
    }
}

function Register-UserCommandShims {
    Param(
        [string]$VenvPath
    )

    $ShimDir = Join-Path $HOME ".cadiax\\bin"
    New-Item -ItemType Directory -Force -Path $ShimDir | Out-Null

    $CadiaxExe = Join-Path $VenvPath "Scripts\\cadiax.exe"
    $TelegramExe = Join-Path $VenvPath "Scripts\\cadiax-telegram.exe"
    $CadiaxCmd = "@echo off`r`n""$CadiaxExe"" %*`r`n"
    $TelegramCmd = "@echo off`r`n""$TelegramExe"" %*`r`n"

    Set-Content -Path (Join-Path $ShimDir "cadiax.cmd") -Value $CadiaxCmd -Encoding ascii
    Set-Content -Path (Join-Path $ShimDir "cadiax-telegram.cmd") -Value $TelegramCmd -Encoding ascii

    $CurrentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($null -eq $CurrentUserPath) {
        $CurrentUserPath = ""
    }
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
        cadiax_cmds = @(
            (Join-Path $ShimDir "cadiax.cmd")
        )
    }
}

function Register-PowerShellProfileShims {
    Param(
        [string]$CadiaxCmd,
        [string]$TelegramCmd
    )

    $MarkerStart = "# >>> Cadiax profile shim >>>"
    $MarkerEnd = "# <<< Cadiax profile shim <<<"
    $Snippet = @(
        $MarkerStart,
        "function global:cadiax { & '$CadiaxCmd' @args }",
        "function global:cadiax-telegram { & '$TelegramCmd' @args }",
        $MarkerEnd
    ) -join "`r`n"

    $DocumentsRoot = [Environment]::GetFolderPath("MyDocuments")
    $ProfilePaths = @(
        $PROFILE.CurrentUserAllHosts,
        (Join-Path $DocumentsRoot "PowerShell\profile.ps1"),
        (Join-Path $DocumentsRoot "PowerShell\Microsoft.PowerShell_profile.ps1"),
        (Join-Path $DocumentsRoot "WindowsPowerShell\profile.ps1"),
        (Join-Path $DocumentsRoot "WindowsPowerShell\Microsoft.PowerShell_profile.ps1")
    ) | Select-Object -Unique

    $UpdatedProfiles = @()
    foreach ($ProfilePath in $ProfilePaths) {
        $ProfileDir = Split-Path -Parent $ProfilePath
        New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null
        if (-not (Test-Path $ProfilePath)) {
            New-Item -ItemType File -Force -Path $ProfilePath | Out-Null
        }

        $Current = Get-Content $ProfilePath -Raw -ErrorAction SilentlyContinue
        $Updated = $false
        if ($Current -match [regex]::Escape($MarkerStart)) {
            $Pattern = [regex]::Escape($MarkerStart) + ".*?" + [regex]::Escape($MarkerEnd)
            $Replacement = [System.Text.RegularExpressions.Regex]::Replace($Current, $Pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $Snippet }, [System.Text.RegularExpressions.RegexOptions]::Singleline)
            if ($Replacement -ne $Current) {
                Set-Content -Path $ProfilePath -Value $Replacement -Encoding utf8
                $Updated = $true
            }
        } else {
            $Prefix = if ($Current -and -not $Current.EndsWith("`r`n") -and -not $Current.EndsWith("`n")) { "`r`n" } else { "" }
            Set-Content -Path $ProfilePath -Value ($Current + $Prefix + $Snippet + "`r`n") -Encoding utf8
            $Updated = $true
        }

        $UpdatedProfiles += @{
            path = $ProfilePath
            updated = $Updated
        }
    }

    return @{
        profiles = $UpdatedProfiles
    }
}

function Sync-AppAssets {
    Param(
        [string]$SourceRoot,
        [string]$AppRoot
    )

    $SourceDashboard = Join-Path $SourceRoot "monitoring-dashboard"
    if (Test-Path $SourceDashboard) {
        $TargetDashboard = Join-Path $AppRoot "monitoring-dashboard"
        if (Test-Path $TargetDashboard) {
            Remove-Item -Recurse -Force $TargetDashboard
        }
        Copy-Item -Recurse -Force $SourceDashboard $TargetDashboard
    }
}

if (-not $AppRoot) {
    $AppRoot = Get-DefaultAppRoot
}
$AppRoot = [System.IO.Path]::GetFullPath($AppRoot)
if (-not $VenvPath) {
    $VenvPath = Join-Path $AppRoot "venv"
}
$VenvPath = [System.IO.Path]::GetFullPath($VenvPath)
$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Mode -eq "uninstall") {
    Invoke-Uninstall -AppRoot $AppRoot -PurgeData:$PurgeData
    exit 0
}

Ensure-PythonReady -Command $PythonCommand

if (-not (Test-Command "git")) {
    Ensure-WingetPackage -Id "Git.Git" -Label "Git"
}

if ($InstallNode -and -not (Test-Command "node")) {
    Ensure-WingetPackage -Id "OpenJS.NodeJS.LTS" -Label "Node.js LTS"
}

Show-PreflightSummary -PythonCommand $PythonCommand -InstallNodeRequested $InstallNode

New-Item -ItemType Directory -Force -Path $AppRoot | Out-Null
Sync-AppAssets -SourceRoot $SourceRoot -AppRoot $AppRoot

if ($Mode -eq "install" -and (Test-Path $VenvPath)) {
    throw "Cadiax sudah terinstall di $AppRoot. Gunakan -Mode reinstall untuk memperbarui instalasi, atau -Mode uninstall untuk menghapusnya."
}

if ((Test-Path $VenvPath) -and ($Mode -eq "reinstall") -and (-not $ReuseVenv)) {
    Reset-VenvDirectory -TargetPath $VenvPath
}

if ((Test-Path $VenvPath) -and $ReuseVenv) {
    Write-Step "Menggunakan virtual environment yang sudah ada di $VenvPath"
} else {
    Write-Step "Menyiapkan virtual environment $VenvPath"
    Invoke-CheckedCommand -Label "python -m venv" -Command @($PythonCommand, "-m", "venv", $VenvPath)
}

$VenvPython = Join-Path $VenvPath "Scripts\\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment gagal dibuat."
}

Write-Step "Menyiapkan pip"
Invoke-CheckedCommand -Label "ensurepip" -Command @($VenvPython, "-m", "ensurepip", "--upgrade")

Write-Step "Mengupgrade pip"
Invoke-CheckedCommand -Label "pip install --upgrade pip" -Command @($VenvPython, "-m", "pip", "install", "--upgrade", "pip")

Write-Step "$(if ($Mode -eq 'reinstall') { 'Memperbarui' } else { 'Menginstall' }) Cadiax"
Invoke-CheckedCommand -Label "pip install source package" -Command @($VenvPython, "-m", "pip", "install", $SourceRoot)

Write-Step "Menyiapkan dokumen workspace aktif"
Invoke-CheckedCommand -Label "cadiax bootstrap foundation" -Command @($VenvPython, "-m", "cadiax.cli", "bootstrap", "foundation")

$ShimInfo = $null
$ProfileInfo = $null
if (-not $SkipUserShim) {
    Write-Step "Mendaftarkan command Cadiax ke user PATH"
    $ShimInfo = Register-UserCommandShims -VenvPath $VenvPath
    if (-not $SkipPowerShellProfileShim) {
        Write-Step "Mendaftarkan shim PowerShell untuk Cadiax"
        $ProfileInfo = Register-PowerShellProfileShims -CadiaxCmd $ShimInfo.cadiax_cmd -TelegramCmd $ShimInfo.telegram_cmd
    }
}

if ($InstallNode) {
    Write-Step "Menyiapkan dashboard dependency"
    Invoke-CheckedCommand -Label "cadiax dashboard install" -Command @($VenvPython, "-m", "cadiax.cli", "dashboard", "install")
}

if (-not $SkipSetup) {
    Write-Step "Menjalankan Cadiax setup"
    Invoke-CheckedCommand -Label "cadiax setup" -Command @($VenvPython, "-m", "cadiax.cli", "setup")
}

Show-NextSteps -VenvPath $VenvPath -VenvPython $VenvPython -AppRoot $AppRoot -ShimInfo $ShimInfo -ProfileInfo $ProfileInfo
if ($ShimInfo) {
    Write-Host ""
    Write-Host "User command shims:"
    Write-Host "- cadiax: $($ShimInfo.cadiax_cmd)"
    Write-Host "- cadiax-telegram: $($ShimInfo.telegram_cmd)"
    Write-Host "- user PATH updated: $($ShimInfo.shim_dir)"
    Write-Host "Buka shell baru agar command `cadiax` memakai shim Cadiax yang baru."
}
