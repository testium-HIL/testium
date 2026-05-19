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

REM ---------- per-mode launcher ----------------------------------------------

echo -- validation mode: %MODE%

IF /I "%MODE%"=="source"      GOTO MODE_SOURCE
IF /I "%MODE%"=="wheel"       GOTO MODE_WHEEL
IF /I "%MODE%"=="pyinstaller" GOTO MODE_PYI
echo ERROR: unknown --mode '%MODE%'. Expected: source ^| wheel ^| pyinstaller.
exit /b 1

:MODE_SOURCE
call "%PROJECT_DIR%\run.bat" %TAIL%
exit /b %ERRORLEVEL%

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
    call "%WHEEL_VENV%\Scripts\pip" install --quiet "%WHEEL%"
)
"%WHEEL_VENV%\Scripts\python.exe" -m testium %TAIL%
exit /b %ERRORLEVEL%

:MODE_PYI
SET "PYI_BIN=%PROJECT_DIR%\dist\testium-%VERSION%.exe"
IF NOT EXIST "%PYI_BIN%" SET "PYI_BIN=%PROJECT_DIR%\dist\testium-%VERSION%"
IF NOT EXIST "%PYI_BIN%" (
    echo ERROR: PyInstaller binary not found in %PROJECT_DIR%\dist -- run build_all.sh first.
    exit /b 1
)
"%PYI_BIN%" %TAIL%
exit /b %ERRORLEVEL%
