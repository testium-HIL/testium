:: @echo off
SETLOCAL EnableExtensions

SET "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

:: --- CONFIGURATION ---
SET "APPNAME=testium"
SET "VENV_DIR=%BASE_DIR%test\tmp\%APPNAME%_venv"
SET "PYTHON_EXE=python"
SET "SCRIPT_NAME=src\%APPNAME%"
SET "REQUIREMENTS=src\requirements.txt"

echo [1/4] Verification of Python...

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

:: If we reach here, python could not be found
echo.
echo ###########################################################
echo ERROR : Python could not be found on this system.
echo ###########################################################
pause
exit /b

:PYTHON_FOUND

:: --- VENV creation ---
if not exist "%VENV_DIR%" (
    echo [2/4] Virtual environment creation...
    %PYTHON_EXE% -m venv %VENV_DIR%
    if %ERRORLEVEL% neq 0 (
        echo ERROR while creating the venv.
        pause
        exit /b
    )
) else (
    echo [2/4] Virtual environment already here.
)

:: --- ACTIVATION AND DEPENDANCES ---
echo [3/4] Activation of the venv and installation of dependencies...
call "%VENV_DIR%\Scripts\activate"

if exist "%BASE_DIR%%REQUIREMENTS%" (
    pip install --upgrade pip
    pip install -r "%BASE_DIR%%REQUIREMENTS%"
) else (
    echo Info : No '%REQUIREMENTS%' file found, dependencies ignored.
)

:: --- Application launching ---
echo [4/4] Launch of  %APPNAME%...
python "%BASE_DIR%%SCRIPT_NAME%"

:: --- FIN ---
echo.
echo %APPNAME% finished
deactivate