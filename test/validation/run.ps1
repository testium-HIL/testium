# Windows counterpart of run.sh: runs the validation suite against a channel
# of testium (source, wheel, pyinstaller). Flatpak/appimage are Linux-only.
#
# Usage:
#   test\validation\run.ps1 [clean] [--mode MODE] [--gui] [extra testium args]
#
#   clean           recreate the validation venv (must be the first argument)
#   --gui           run the suite through the GUI (-r: opens, runs, closes);
#                   the log goes to a temp file and the post-check result is
#                   printed at the end
#   --mode MODE     source (default) | wheel | pyinstaller
#
# Test-execution subprocesses run in a host venv under
# %TEMP%\testium-validation-venv, shared across modes. Reports are suffixed
# with the mode so successive runs don't overwrite each other.

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Resolve-Path (Join-Path $scriptDir '..\..')
$version = (Get-Content (Join-Path $projectDir 'src\VERSION') -Raw).Trim()

function Fail($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

# Native tools don't trip $ErrorActionPreference - check their exit code.
function Invoke-Checked {
    param([string]$What, [string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { Fail "$What failed (exit $LASTEXITCODE)." }
}

# True if `python -c <Code>` succeeds. Discarding the output would turn the
# expected stderr traceback into a terminating NativeCommandError under
# $ErrorActionPreference='Stop', hence the local reset.
function Test-Import {
    param([string]$Python, [string]$Code)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        # -I keeps the current directory out of sys.path: a package source
        # tree in the working directory must not satisfy the check.
        & $Python -I -c $Code *> $null
        return ($LASTEXITCODE -eq 0)
    } finally { $ErrorActionPreference = $prev }
}

# ---------- arg parsing -------------------------------------------------------

$mode = 'source'
$clean = $false
$gui = $false
$extra = @()

$rest = @($args)
if ($rest.Count -gt 0 -and $rest[0] -in @('clean', '-clean', '--clean')) {
    $clean = $true
    $rest = @($rest | Select-Object -Skip 1)
}

for ($i = 0; $i -lt $rest.Count; $i++) {
    $a = [string]$rest[$i]
    switch -Regex ($a) {
        '^--mode$'   { $mode = [string]$rest[++$i] }
        '^--mode=.*' { $mode = $a.Substring(7) }
        '^--?gui$'   { $gui = $true }
        default      { $extra += $a }
    }
}

# batch by default; --gui runs through the GUI with -r (run and close) and
# logs to a temp file, echoed back after the run.
$runFlags = @('-b')
$guiLog = ''
if ($gui) {
    $guiLog = Join-Path $env:TEMP "testium-validation-$mode.log"
    if (Test-Path $guiLog) { Remove-Item -Force $guiLog }
    $runFlags = @('-r', '-l', $guiLog)
}

# ---------- locate host python ------------------------------------------------

$python = (Get-Command py.exe -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source }
if (-not $python) { Fail "Python could not be found on this system." }

# ---------- validation venv ---------------------------------------------------

$venvDir = Join-Path $env:TEMP 'testium-validation-venv'
if ($clean -and (Test-Path $venvDir)) { Remove-Item -Recurse -Force $venvDir }

if (-not (Test-Path $venvDir)) {
    Write-Host "Creating validation venv at $venvDir"
    Invoke-Checked 'venv creation' $python @('-m', 'venv', '--system-site-packages', $venvDir)
    Invoke-Checked 'pip upgrade' (Join-Path $venvDir 'Scripts\pip.exe') @('install', '--quiet', '--upgrade', 'pip')
}
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$venvPip = Join-Path $venvDir 'Scripts\pip.exe'

# Probed, not installed once at creation, so an older venv picks up new deps.
if (-not (Test-Import $venvPython 'import junit_xml, pytest, jsonschema, yaml')) {
    Write-Host "Installing validation dependencies into $venvDir"
    Invoke-Checked 'validation deps' $venvPip @('install', '--quiet', 'junit-xml', 'pytest', 'jsonschema', 'pyyaml')
}

# Exporter plugins are discovered by export_worker.py, which runs on the host
# python passed as python_bin below - so fake_exporter goes in this venv.
if (-not (Test-Import $venvPython 'import fake_exporter')) {
    Invoke-Checked 'fake_exporter install' $venvPip @('install', '--quiet', '-e', (Join-Path $scriptDir 'fake_exporter'))
}

# ---------- per-mode launcher -------------------------------------------------

switch ($mode.ToLower()) {
    'source' {
        # Not delegated to the project's run.ps1: it activates a venv and
        # pauses on error, which a head-less suite must not depend on.
        $testiumVenv = Join-Path $projectDir 'test\tmp\testium_venv'
        if (-not (Test-Path $testiumVenv)) {
            Write-Host "Creating testium venv at $testiumVenv"
            Invoke-Checked 'venv creation' $python @('-m', 'venv', $testiumVenv)
            $pip = Join-Path $testiumVenv 'Scripts\pip.exe'
            Invoke-Checked 'pip upgrade' $pip @('install', '--quiet', '--upgrade', 'pip')
            Invoke-Checked 'testium deps' $pip @('install', '--quiet', '-r', (Join-Path $projectDir 'src\requirements.txt'))
            # language-server extra so `testium lsp` works from source
            Invoke-Checked 'pygls install' $pip @('install', '--quiet', 'pygls>=1.3')
        }
        $cmd = @((Join-Path $testiumVenv 'Scripts\python.exe'), (Join-Path $projectDir 'src\testium'))
    }
    'wheel' {
        $wheel = Join-Path $projectDir "dist\testium_hil-$version-py3-none-any.whl"
        if (-not (Test-Path $wheel)) { Fail "wheel not found at $wheel - run .\build_all.ps1 first." }
        $wheelVenv = Join-Path $env:TEMP "testium-wheel-venv-$version"
        if ($clean -and (Test-Path $wheelVenv)) { Remove-Item -Recurse -Force $wheelVenv }
        if (-not (Test-Path $wheelVenv)) {
            Write-Host "Creating wheel venv at $wheelVenv"
            Invoke-Checked 'venv creation' $python @('-m', 'venv', '--system-site-packages', $wheelVenv)
            $pip = Join-Path $wheelVenv 'Scripts\pip.exe'
            Invoke-Checked 'pip upgrade' $pip @('install', '--quiet', '--upgrade', 'pip')
            # [lsp] extra: validate the wheel in its language-server form
            Invoke-Checked 'wheel install' $pip @('install', '--quiet', "$wheel[lsp]")
        }
        $cmd = @((Join-Path $wheelVenv 'Scripts\python.exe'), '-m', 'testium')
    }
    'pyinstaller' {
        # build_all.ps1 zips the one-folder build and leaves it in
        # package\pyinstaller\dist; also accept an unpacked copy in dist\.
        $candidates = @(
            (Join-Path $projectDir "dist\testium-$version.exe"),
            (Join-Path $projectDir "dist\testium-$version\testium.exe"),
            (Join-Path $projectDir 'package\pyinstaller\dist\testium\testium.exe')
        )
        $pyiBin = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
        if (-not $pyiBin) {
            Fail "PyInstaller binary not found ($($candidates -join ', ')) - run .\build_all.ps1 first."
        }
        $cmd = @($pyiBin)
    }
    default {
        Fail "unknown --mode '$mode'. Expected: source | wheel | pyinstaller."
    }
}

# ---------- launch ------------------------------------------------------------

Write-Host "-- validation mode: $mode"
Write-Host "-- launch: $($cmd -join ' ')"

# Per-channel pre-checks, same set and order as run.sh.
Write-Host "-- LSP check ($mode)"
Invoke-Checked "LSP check ($mode)" $venvPython (@((Join-Path $scriptDir 'lsp_check.py')) + $cmd)

Write-Host "-- schema check ($mode)"
Invoke-Checked "schema check ($mode)" $venvPython (@((Join-Path $scriptDir 'schema_check.py')) + $cmd)

Write-Host "-- load-error check ($mode)"
Invoke-Checked "load-error check ($mode)" $venvPython (@((Join-Path $scriptDir 'load_errors_check.py')) + $cmd)

# Step and GUI checks import the interpreter / main_win, so source mode only,
# and they need the testium venv (PySide6, requirements).
if ($mode.ToLower() -eq 'source') {
    $devPython = Join-Path $projectDir 'test\tmp\testium_venv\Scripts\python.exe'
    if (-not (Test-Path $devPython)) { $devPython = $venvPython }

    Write-Host "-- step check ($mode)"
    Invoke-Checked "step check ($mode)" $devPython @((Join-Path $scriptDir 'step_check.py'))

    Write-Host "-- gd restore check ($mode)"
    Invoke-Checked "gd restore check ($mode)" $devPython @((Join-Path $scriptDir 'gd_restore_check.py'))

    Write-Host "-- GUI reload check ($mode)"
    Invoke-Checked "GUI reload check ($mode)" $devPython @((Join-Path $scriptDir 'gui_reload_check.py'))

    Write-Host "-- GUI state check ($mode)"
    Invoke-Checked "GUI state check ($mode)" $devPython @((Join-Path $scriptDir 'gui_state_check.py'))
}

if ($gui) {
    Write-Host "-- GUI mode: the suite runs in the GUI window (log: $guiLog)."
}

# $extra before "--": forwarded arguments are options (-d ...), the test
# file is the only positional.
$tail = $runFlags + @(
    '-d', "python_bin=$venvPython",
    '-d', "validation_report_file=validation-$mode"
) + $extra + @('--', (Join-Path $scriptDir 'main.tum'))

$exe = $cmd[0]
$cmdArgs = @($cmd | Select-Object -Skip 1) + $tail
if ($gui) {
    # windowed exe (frozen build): piping stdout forces PowerShell to wait
    & $exe @cmdArgs | Out-Null
} else {
    & $exe @cmdArgs
}
$rc = $LASTEXITCODE

# GUI mode: the run log went to the file, show the post-check result.
if ($gui) {
    Write-Host "-- log file: $guiLog"
    if (-not (Test-Path $guiLog)) {
        Write-Host "WARNING: log file not created." -ForegroundColor Yellow
    } else {
        $hit = Select-String -Path $guiLog -Pattern 'Post execution started' -SimpleMatch | Select-Object -First 1
        if ($hit) {
            Get-Content $guiLog | Select-Object -Skip ($hit.LineNumber - 2) | Write-Host
        } else {
            Write-Host "WARNING: no post-execution result found in the log." -ForegroundColor Yellow
        }
    }
}
exit $rc
