@echo off
SETLOCAL EnableExtensions EnableDelayedExpansion

REM Runs the testium validation suite against any installable channel of
REM testium on Windows (source, wheel, pyinstaller).
REM
REM Usage:
REM   test\validation\run.bat [clean] [--mode MODE] [extra testium args]
REM
REM   clean       remove the validation venv before recreating it
REM               (must be the first argument; useful after a Python upgrade)
REM
REM   --mode MODE which testium build to validate. One of:
REM                   source       (default) project's run.bat (src\testium)
REM                   wheel        dist\testium-<v>-py3-none-any.whl
REM                   pyinstaller  dist\testium-<v>.exe (or dist\testium-<v>)
REM
REM Every test-execution subprocess runs in a dedicated host venv under
REM %TEMP%\testium-validation-venv (created with --system-site-packages,
REM then junit-xml is pip-installed for post_execution.py).
REM
REM The report file is suffixed with the mode so consecutive runs in
REM different modes don't overwrite each other.

SET "SCRIPT_DIR=%~dp0"
IF "%SCRIPT_DIR:~-1%"=="\" SET "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
SET "PROJECT_DIR=%SCRIPT_DIR%\..\.."
SET /P VERSION=<"%PROJECT_DIR%\src\VERSION"

REM ---------- arg parsing ----------------------------------------------------

SET "MODE=source"
SET "CLEAN=0"
IF /I "%~1"=="clean" (
    SET "CLEAN=1"
    SHIFT
)

SET "EXTRA="
:PARSE_ARGS
IF "%~1"=="" GOTO ARGS_DONE
IF /I "%~1"=="--mode" (
    SET "MODE=%~2"
    SHIFT
    SHIFT
    GOTO PARSE_ARGS
)
SET "EXTRA=!EXTRA! "%~1""
SHIFT
GOTO PARSE_ARGS
:ARGS_DONE

REM ---------- locate host python ---------------------------------------------

SET "PYTHON_EXE="
py --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET "PYTHON_EXE=py"
    GOTO PYTHON_FOUND
)
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET "PYTHON_EXE=python"
    GOTO PYTHON_FOUND
)
echo ERROR: Python could not be found on this system.
exit /b 1
:PYTHON_FOUND

REM ---------- validation venv -------------------------------------------------

SET "VENV_DIR=%TEMP%\testium-validation-venv"
IF "%CLEAN%"=="1" IF EXIST "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"

IF NOT EXIST "%VENV_DIR%" (
    echo Creating validation venv at %VENV_DIR%
    %PYTHON_EXE% -m venv --system-site-packages "%VENV_DIR%"
    IF !ERRORLEVEL! NEQ 0 (
        echo ERROR while creating the validation venv.
        exit /b 1
    )
    call "%VENV_DIR%\Scripts\pip" install --quiet --upgrade pip
    call "%VENV_DIR%\Scripts\pip" install --quiet junit-xml
)
SET "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

REM ---------- shared "tail" forwarded to every launcher -----------------------
REM Reports are stamped with the mode so successive runs don't clobber each other.

SET "TAIL=-b -d "python_bin=%VENV_PYTHON%" -d "validation_report_file=validation-%MODE%" -- "%SCRIPT_DIR%\main.tum"%EXTRA%"

REM The report-exporter plugin (items\report_plugin) is a pip entry-point
REM package. It must live in the *testium* environment, so it is installed into
REM the source/wheel venvs below. A frozen PyInstaller binary cannot see
REM externally-installed plugins, so report_plugin is expected to be skipped
REM there (same as Linux pyinstaller mode).
SET "FAKE_EXPORTER=%SCRIPT_DIR%\fake_exporter"

REM ---------- per-mode launcher ----------------------------------------------

echo -- validation mode: %MODE%

IF /I "%MODE%"=="source"      GOTO MODE_SOURCE
IF /I "%MODE%"=="wheel"       GOTO MODE_WHEEL
IF /I "%MODE%"=="pyinstaller" GOTO MODE_PYI
echo ERROR: unknown --mode '%MODE%'. Expected: source ^| wheel ^| pyinstaller.
exit /b 1

:MODE_SOURCE
REM Run testium from src\ in a dedicated venv set up here. We do NOT delegate to
REM the project's run.bat: that one launches the GUI and does not forward its
REM arguments, so the suite would never run head-less.
SET "TESTIUM_VENV=%PROJECT_DIR%\test\tmp\testium_venv"
IF NOT EXIST "%TESTIUM_VENV%" (
    echo Creating testium venv at %TESTIUM_VENV%
    %PYTHON_EXE% -m venv "%TESTIUM_VENV%"
    IF !ERRORLEVEL! NEQ 0 (
        echo ERROR while creating the testium venv.
        exit /b 1
    )
    call "%TESTIUM_VENV%\Scripts\pip" install --quiet --upgrade pip
    call "%TESTIUM_VENV%\Scripts\pip" install --quiet -r "%PROJECT_DIR%\src\requirements.txt"
    REM language-server extra so `testium lsp` works from source (lsp_check.py)
    call "%TESTIUM_VENV%\Scripts\pip" install --quiet "pygls>=1.3"
)
call "%TESTIUM_VENV%\Scripts\pip" install --quiet -e "%FAKE_EXPORTER%"
SET CMD="%TESTIUM_VENV%\Scripts\python.exe" "%PROJECT_DIR%\src\testium"
GOTO LAUNCH

:MODE_WHEEL
SET "WHEEL=%PROJECT_DIR%\dist\testium-%VERSION%-py3-none-any.whl"
IF NOT EXIST "%WHEEL%" (
    echo ERROR: wheel not found at %WHEEL% -- run build_all.sh first.
    exit /b 1
)
SET "WHEEL_VENV=%TEMP%\testium-wheel-venv-%VERSION%"
IF "%CLEAN%"=="1" IF EXIST "%WHEEL_VENV%" rmdir /s /q "%WHEEL_VENV%"
IF NOT EXIST "%WHEEL_VENV%" (
    echo Creating wheel venv at %WHEEL_VENV%
    %PYTHON_EXE% -m venv --system-site-packages "%WHEEL_VENV%"
    call "%WHEEL_VENV%\Scripts\pip" install --quiet --upgrade pip
    REM install with the [lsp] extra so the wheel channel is validated in its
    REM language-server-capable form (pulls pygls), matching `pip install testium[lsp]`.
    call "%WHEEL_VENV%\Scripts\pip" install --quiet "%WHEEL%[lsp]"
)
call "%WHEEL_VENV%\Scripts\pip" install --quiet -e "%FAKE_EXPORTER%"
SET CMD="%WHEEL_VENV%\Scripts\python.exe" -m testium
GOTO LAUNCH

:MODE_PYI
SET "PYI_BIN=%PROJECT_DIR%\dist\testium-%VERSION%.exe"
IF NOT EXIST "%PYI_BIN%" SET "PYI_BIN=%PROJECT_DIR%\dist\testium-%VERSION%"
IF NOT EXIST "%PYI_BIN%" (
    echo ERROR: PyInstaller binary not found in %PROJECT_DIR%\dist -- run build_all.sh first.
    exit /b 1
)
SET CMD="%PYI_BIN%"
GOTO LAUNCH

REM ---------- launch ----------------------------------------------------------

:LAUNCH
echo -- launch: %CMD%

REM LSP check (this exact channel): `schema` must keep its nested actions and
REM `lsp` must answer initialize. Mirrors run.sh; aborts the run on failure.
echo -- LSP check (%MODE%)
"%VENV_PYTHON%" "%SCRIPT_DIR%\lsp_check.py" %CMD%
IF !ERRORLEVEL! NEQ 0 (
    echo ERROR: LSP check failed for mode %MODE%.
    exit /b 1
)

%CMD% %TAIL%
exit /b %ERRORLEVEL%
