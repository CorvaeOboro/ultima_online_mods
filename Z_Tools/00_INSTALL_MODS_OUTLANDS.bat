:: ULTIMA ONLINE MODS - PYTHON TOOLS SETUP AND LAUNCHER
:: Creates a virtual environment, installs requirements, starts mod selector

@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

:: Set working directory to script location
cd /d "%~dp0"

:: Configurable paths
set "VENV_DIR=venv"
set "REQUIREMENTS=requirements.txt"
set "LOG_DIR=logs"

:: Create logs folder if not exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: ===================================================
:: HEADER
:: ===================================================
echo.
echo ===================================================
echo   ULTIMA ONLINE MODS - Python Tools Setup
echo ===================================================
echo.
echo [INFO] Current directory: %CD%
echo.

:: ===================================================
:: CHECK FOR PYTHON
:: ===================================================
echo [STEP 1/4] Checking for Python installation...
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is NOT installed or NOT found in PATH!
    echo.
    echo -----------------------------------------------
    echo   HOW TO INSTALL PYTHON:
    echo -----------------------------------------------
    echo 1. Download Python from: https://www.python.org/downloads/
    echo    Recommended: Python 3.10 or 3.11
    echo.
    echo 2. Run the installer and IMPORTANT:
    echo    [X] CHECK "Add Python to PATH" checkbox
    echo        ^(at the bottom of the installer^)
    echo.
    echo 3. After installation, restart this script
    echo.
    echo ALTERNATIVE: If Python is installed but not in PATH:
    echo - Reinstall Python with "Add to PATH" checked
    echo - OR manually add Python to your PATH environment variable
    echo -----------------------------------------------
    echo.
    pause
    exit /b 1
)

:: Get Python path and version
for /f "delims=" %%i in ('where python') do set "PYTHON_PATH=%%i"
echo [OK] Python found at: %PYTHON_PATH%

for /f "tokens=2 delims= " %%v in ('python --version 2^>nul') do set "PYTHON_VERSION=%%v"
echo [OK] Python version: %PYTHON_VERSION%
echo.

:: Check Python version (3.8+)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)

if %PY_MAJOR% LSS 3 (
    echo [WARNING] Python 3.8 or higher is recommended. Current: %PYTHON_VERSION%
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "!CONTINUE!"=="y" exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 8 (
    echo [WARNING] Python 3.8 or higher is recommended. Current: %PYTHON_VERSION%
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "!CONTINUE!"=="y" exit /b 1
)

:: ===================================================
:: CHECK FOR PIP
:: ===================================================
echo [STEP 2/4] Checking for pip (Python package manager)...
echo.

python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed or not working!
    echo.
    echo Try reinstalling Python with pip included.
    echo.
    pause
    exit /b 1
)

for /f "delims=" %%p in ('python -m pip --version') do set "PIP_VERSION=%%p"
echo [OK] Pip found: %PIP_VERSION%
echo.

:: ===================================================
:: CHECK REQUIREMENTS FILE
:: ===================================================
if not exist "%REQUIREMENTS%" (
    echo [ERROR] requirements.txt not found!
    echo Expected at: %CD%\%REQUIREMENTS%
    echo.
    pause
    exit /b 1
)

echo [INFO] Requirements file found: %REQUIREMENTS%
echo.

:: ===================================================
:: VIRTUAL ENVIRONMENT SETUP
:: ===================================================
echo [STEP 3/4] Setting up virtual environment...
echo.

:: Check if venv exists and is valid
set "VENV_OK=1"
if exist "%VENV_DIR%\" (
    echo [INFO] Virtual environment folder exists. Checking integrity...
    
    if not exist "%VENV_DIR%\Scripts\activate.bat" set "VENV_OK=0"
    if not exist "%VENV_DIR%\Scripts\python.exe" set "VENV_OK=0"
    if not exist "%VENV_DIR%\Scripts\pip.exe" set "VENV_OK=0"
    
    if !VENV_OK!==0 (
        echo [WARNING] Virtual environment appears incomplete or corrupted.
        set /p RECREATE="Delete and recreate virtual environment? (y/n): "
        if /i "!RECREATE!"=="y" (
            echo [INFO] Deleting old virtual environment...
            rmdir /s /q "%VENV_DIR%"
            if exist "%VENV_DIR%\" (
                echo [ERROR] Failed to delete venv folder. Please delete manually.
                pause
                exit /b 1
            )
        ) else (
            echo [ERROR] Cannot proceed with corrupted virtual environment.
            pause
            exit /b 1
        )
    ) else (
        echo [OK] Virtual environment is valid.
        
        :: Check if requirements are newer than venv
        set "VENVTIME="
        set "REQTIME="
        for %%F in ("%VENV_DIR%\Scripts\activate.bat") do set "VENVTIME=%%~tF"
        for %%F in ("%REQUIREMENTS%") do set "REQTIME=%%~tF"
        
        if "!REQTIME!" GTR "!VENVTIME!" (
            echo [INFO] requirements.txt has been updated since venv creation.
            set /p REINSTALL="Reinstall dependencies? (y/n): "
            if /i "!REINSTALL!"=="y" goto :install_requirements
            echo [INFO] Skipping dependency reinstall.
            goto :launch_menu
        ) else (
            echo [INFO] Dependencies are up-to-date.
            goto :launch_menu
        )
    )
)

:: Create new virtual environment
if not exist "%VENV_DIR%\" (
    echo [INFO] Creating new virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        echo.
        echo This might happen if:
        echo - Python installation is incomplete
        echo - Insufficient disk space
        echo - Antivirus blocking the operation
        echo.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
    echo.
)

:: ===================================================
:: INSTALL REQUIREMENTS
:: ===================================================
:install_requirements
echo [STEP 4/4] Installing Python packages...
echo.

call "%VENV_DIR%\Scripts\activate.bat"

echo [INFO] Installing packages from requirements.txt...
echo.
python -m pip install --upgrade pip
python -m pip install -r "%REQUIREMENTS%"

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install some packages!
    echo.
    set /p RETRY="Try recreating virtual environment? (y/n): "
    if /i "!RETRY!"=="y" (
        deactivate
        rmdir /s /q "%VENV_DIR%"
        echo [INFO] Recreating virtual environment...
        python -m venv "%VENV_DIR%"
        if errorlevel 1 (
            echo [ERROR] Failed to create virtual environment.
            pause
            exit /b 1
        )
        call "%VENV_DIR%\Scripts\activate.bat"
        python -m pip install --upgrade pip
        python -m pip install -r "%REQUIREMENTS%"
        if errorlevel 1 (
            echo [ERROR] Installation failed again. Check your internet connection.
            deactivate
            pause
            exit /b 1
        )
    ) else (
        deactivate
        pause
        exit /b 1
    )
)

deactivate
echo.
echo [OK] All packages installed successfully!
echo.

:: ===================================================
:: LAUNCH MOD SELECTOR
:: ===================================================
:launch_menu
echo ===================================================
echo   SETUP COMPLETE!
echo ===================================================
echo.
echo Virtual environment ready at: %CD%\%VENV_DIR%
echo.
echo [INFO] Launching Mod Selector...
echo.

:: Launch the mod selector tool
call "%VENV_DIR%\Scripts\activate.bat"
python "00_psd_to_GumpOverrides.py"
deactivate

echo.
echo [INFO] Mod Selector closed.
echo.
endlocal
pause
exit /b 0
