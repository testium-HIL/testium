# Windows equivalent of build_all.sh. Builds every Windows channel into dist\:
#   1. Wheel           -> dist\testium-<v>-py3-none-any.whl
#   2. PyInstaller exe -> dist\testium-<v>\  (one-folder) + testium-<v>-win64.zip
#   3. Installer       -> dist\testium-<v>-setup.exe  (Inno Setup, per-user)
#   4. Manual PDF      -> dist\testium-manual-<v>.pdf  (only with -Manual)
#
# Flatpak / AppImage are Linux-only and intentionally absent here.
# A step is skipped if its artifact already exists; -Clean forces a rebuild.
#
# Usage: .\build_all.ps1 [-Clean] [-Manual]

[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$Manual
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$distDir = Join-Path $root 'dist'
$version = (Get-Content (Join-Path $root 'src\VERSION') -Raw).Trim()
New-Item -ItemType Directory -Force $distDir | Out-Null

function Step($msg) {
    Write-Host ''
    Write-Host '================================================================' -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host '================================================================' -ForegroundColor Cyan
}

# ---------- artifact paths ----------
$wheel = Join-Path $distDir "testium-$version-py3-none-any.whl"
$onedir = Join-Path $root 'package\pyinstaller\dist\testium'
$zip = Join-Path $distDir "testium-$version-win64.zip"
$setup = Join-Path $distDir "testium-$version-setup.exe"
$manualPdf = Join-Path $distDir "testium-manual-$version.pdf"

if ($Clean) {
    Write-Host "-- clean: removing dist artifacts for version $version"
    Remove-Item -Force -ErrorAction SilentlyContinue $wheel, $zip, $setup, $manualPdf
}

# ---------- release note ----------
$noteSrc = Join-Path $root 'release_note.txt'
Copy-Item -Force $noteSrc (Join-Path $distDir 'release_note.txt')
if (-not (Select-String -Path $noteSrc -Pattern "^version $([regex]::Escape($version))([^.0-9]|$)" -Quiet)) {
    Write-Warning "release_note.txt has no entry for version $version."
}

# ---------- build venv (reuses the run.ps1 venv) ----------
Step "Prep: build venv + tools"
$py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py.exe -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw "Python not found (install it and add it to PATH)." }

$venv = Join-Path $root 'test\tmp\testium_venv'
if (-not (Test-Path $venv)) {
    Write-Host "Creating build venv at $venv"
    & $py -m venv $venv
}
$venvPy = Join-Path $venv 'Scripts\python.exe'
& $venvPy -m pip install --quiet --upgrade pip
& $venvPy -m pip install --quiet -r (Join-Path $root 'src\requirements.txt')
& $venvPy -m pip install --quiet --upgrade build pyinstaller "pygls>=1.3"

# ---------- 1. wheel ----------
Step "1  Wheel ($version)"
if (Test-Path $wheel) {
    Write-Host "wheel: already built - skipping"
} else {
    Push-Location (Join-Path $root 'src')
    try {
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist, build
        Get-ChildItem -Directory -Filter *.egg-info | Remove-Item -Recurse -Force
        & $venvPy -m build --wheel
        if ($LASTEXITCODE -ne 0) { throw "wheel build failed" }
    } finally { Pop-Location }
    $src = Get-ChildItem (Join-Path $root 'src\dist') -Filter *.whl | Sort-Object LastWriteTime | Select-Object -Last 1
    Copy-Item -Force $src.FullName $wheel
    Write-Host "wheel: done"
}

# ---------- 2. PyInstaller one-folder exe (+ portable zip) ----------
Step "2  PyInstaller one-folder exe ($version)"
if ((Test-Path $zip) -and -not $Clean) {
    Write-Host "pyinstaller: zip already built - skipping"
} else {
    $pyiDir = Join-Path $root 'package\pyinstaller'
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $pyiDir 'build'), (Join-Path $pyiDir 'dist')
    Push-Location $pyiDir
    try {
        $env:TESTIUM_ONEDIR = '1'
        & $venvPy -m PyInstaller 'testium.spec'
        if ($LASTEXITCODE -ne 0) { throw "pyinstaller failed" }
    } finally {
        Remove-Item Env:\TESTIUM_ONEDIR -ErrorAction SilentlyContinue
        Pop-Location
    }
    Remove-Item -Force -ErrorAction SilentlyContinue $zip
    Compress-Archive -Path $onedir -DestinationPath $zip
    Write-Host "pyinstaller: done (folder + $([System.IO.Path]::GetFileName($zip)))"
}

# ---------- 3. Inno Setup installer ----------
Step "3  Installer ($version)"
if ((Test-Path $setup) -and -not $Clean) {
    Write-Host "installer: already built - skipping"
} elseif (-not (Test-Path $onedir)) {
    Write-Warning "installer: skipped - one-folder build missing (run without -Clean skip?)."
} else {
    $iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
    if (-not $iscc) {
        foreach ($p in @(
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe")) {
            if (Test-Path $p) { $iscc = $p; break }
        }
    }
    if (-not $iscc) {
        Write-Warning "installer: ISCC.exe not found - install Inno Setup 6 (winget install --id JRSoftware.InnoSetup -e)."
    } else {
        & $iscc (Join-Path $root 'package\innosetup\testium.iss')
        if ($LASTEXITCODE -ne 0) { throw "ISCC failed" }
        Copy-Item -Force (Join-Path $root "package\innosetup\dist\testium-$version-setup.exe") $setup
        Write-Host "installer: done"
    }
}

# ---------- 4. manual PDF (opt-in: needs sphinx + LaTeX via Git Bash) ----------
if ($Manual) {
    Step "4  Manual PDF ($version)"
    if (Test-Path $manualPdf) {
        Write-Host "manual: already built - skipping"
    } else {
        $bash = (Get-Command bash.exe -ErrorAction SilentlyContinue).Source
        if (-not $bash) {
            Write-Warning "manual: skipped - bash.exe (Git Bash) not found."
        } else {
            & $bash (Join-Path $root 'doc/manual/sphinx/build_doc.sh')
            $pdf = Join-Path $root 'doc\manual\testium_manual.pdf'
            if ($LASTEXITCODE -eq 0 -and (Test-Path $pdf)) {
                Copy-Item -Force $pdf $manualPdf
                Write-Host "manual: done"
            } else {
                Write-Warning "manual: build failed (LaTeX toolchain missing?)."
            }
        }
    }
}

# ---------- summary ----------
Step "All Windows packages built"
Write-Host ("  wheel        : {0}" -f ((Test-Path $wheel) ? $wheel : '(missing)'))
Write-Host ("  portable zip : {0}" -f ((Test-Path $zip) ? $zip : '(missing)'))
Write-Host ("  installer    : {0}" -f ((Test-Path $setup) ? $setup : '(missing)'))
if ($Manual) { Write-Host ("  manual       : {0}" -f ((Test-Path $manualPdf) ? $manualPdf : '(missing)')) }
