@echo off
SETLOCAL EnableExtensions

REM Runs the testium validation suite with a dedicated Python venv used
REM by every py_func / cycle / inline-eval subprocess. testium itself
REM keeps running in the project's own environment; the validation venv
REM only isolates *test execution*.
REM
REM   test\validation\run.bat [clean] [extra testium args]
REM
REM Requires the project venv to already exist (run the project's
REM run.bat once first, or any other testium install method).

SET "SCRIPT_DIR=%~dp0"
SET "PROJECT_DIR=%SCRIPT_DIR%..\.."
REM Venv in the user temp dir (Windows equivalent of /tmp).
SET "VENV_DIR=%TEMP%\testium-validation-venv"
SET "PROJECT_VENV=%PROJECT_DIR%\test\tmp\testium_venv"

IF /I "%~1"=="clean" (
    rmdir /s /q "%VENV_DIR%"
    SHIFT
)

REM Locate a host Python.
SET "PYTHON_EXE=python"
py --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET "PYTHON_EXE=py"
    goto :PYTHON_FOUND
)
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    SET "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)
echo ERROR : Python could not be found on this system.
exit /b 1

:PYTHON_FOUND

IF NOT EXIST "%VENV_DIR%" (
    echo Creating validation venv at %VENV_DIR%
    %PYTHON_EXE% -m venv --system-site-packages "%VENV_DIR%"
    IF %ERRORLEVEL% NEQ 0 (
        echo ERROR while creating the validation venv.
        exit /b 1
    )
    call "%VENV_DIR%\Scripts\pip" install --quiet --upgrade pip
    call "%VENV_DIR%\Scripts\pip" install --quiet junit-xml
)

SET "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

IF NOT EXIST "%PROJECT_VENV%" (
    echo ERROR : project venv not found at %PROJECT_VENV%. Run the project run.bat once first.
    exit /b 1
)

call "%PROJECT_VENV%\Scripts\activate"
python "%PROJECT_DIR%\src\testium" -b -d "python_bin=%VENV_PYTHON%" -- "%SCRIPT_DIR%main.tum" %*
