@echo off
setlocal

title DAILY PLANNER APP - EXE Builder

echo.
echo ==========================================
echo          PLANNER APP EXE BUILDER
echo ==========================================
echo.

REM ------------------------------------------
REM Move to the folder where this BAT exists
REM ------------------------------------------

cd /d "%~dp0"

echo Project folder:
echo %CD%
echo.

REM ------------------------------------------
REM Ask for version
REM ------------------------------------------

set /p VERSION=Enter version (example: 1.0.0): 

if "%VERSION%"=="" (
    echo.
    echo ERROR: Version cannot be empty.
    pause
    exit /b 1
)

set "TAG=v%VERSION%"
set "RELEASE_DIR=releases\%TAG%"
set "EXE_NAME=DailyPlanner-%TAG%.exe"

echo.
echo ==========================================
echo Version: %TAG%
echo Output:  %RELEASE_DIR%
echo ==========================================
echo.

REM ------------------------------------------
REM Check Python
REM ------------------------------------------

echo Checking Python...

python --version

if errorlevel 1 (
    echo.
    echo ERROR: Python was not found.
    echo.
    pause
    exit /b 1
)

echo.

REM ------------------------------------------
REM Install / check PyInstaller
REM ------------------------------------------

echo Checking PyInstaller...

python -m PyInstaller --version

if errorlevel 1 (
    echo PyInstaller not found.
    echo Installing PyInstaller...
    echo.

    python -m pip install pyinstaller

    if errorlevel 1 (
        echo.
        echo ERROR: Could not install PyInstaller.
        pause
        exit /b 1
    )
)

echo.
echo PyInstaller ready.
echo.

REM ------------------------------------------
REM Remove previous build files
REM ------------------------------------------

echo Cleaning previous build files...

if exist "build" (
    rmdir /s /q "build"
)

if exist "dist" (
    rmdir /s /q "dist"
)

if exist "%RELEASE_DIR%" (
    echo.
    echo WARNING:
    echo %RELEASE_DIR% already exists.
    echo.

    choice /M "Do you want to overwrite this version"

    if errorlevel 2 (
        echo.
        echo Build cancelled.
        pause
        exit /b 0
    )

    rmdir /s /q "%RELEASE_DIR%"
)

echo.
echo ==========================================
echo BUILDING DAILYPLANNER %TAG%
echo ==========================================
echo.

REM ------------------------------------------
REM Build EXE
REM ------------------------------------------

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --icon "icon.ico" ^
    --name "DailyPlanner-%TAG%" ^
    "final_code.py"

if errorlevel 1 (
    echo.
    echo ==========================================
    echo              BUILD FAILED
    echo ==========================================
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------
REM Create version folder
REM ------------------------------------------

echo.
echo Creating release folder...

mkdir "%RELEASE_DIR%"

REM ------------------------------------------
REM Move EXE into version folder
REM ------------------------------------------

move /Y "dist\DailyPlanner-%TAG%.exe" "%RELEASE_DIR%\%EXE_NAME%"

if errorlevel 1 (
    echo.
    echo ERROR: Could not move EXE to release folder.
    pause
    exit /b 1
)

REM ------------------------------------------
REM Clean temporary folders
REM ------------------------------------------

if exist "build" (
    rmdir /s /q "build"
)

if exist "dist" (
    rmdir /s /q "dist"
)

REM ------------------------------------------
REM Success
REM ------------------------------------------

echo.
echo ==========================================
echo             BUILD SUCCESSFUL!
echo ==========================================
echo.
echo Version:
echo %TAG%
echo.
echo EXE:
echo %CD%\%RELEASE_DIR%\%EXE_NAME%
echo.
echo ==========================================
echo.

explorer "%CD%\%RELEASE_DIR%"

pause
