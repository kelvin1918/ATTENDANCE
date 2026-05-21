@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: launch.bat  —  BatStateU Attendance Local Station Launcher
:: ─────────────────────────────────────────────────────────────────────────────
:: Place this file inside the AttendanceStation\ folder (beside AttendanceStation.exe)
:: Instructors double-click this file to start the system.
:: ─────────────────────────────────────────────────────────────────────────────

title BatStateU Attendance — Local Station

echo.
echo  =====================================================
echo    BatStateU Attendance Monitoring System
echo    IoT-Based Facial Biometrics Local Station
echo  =====================================================
echo.
echo  Starting server... please wait.
echo  Do NOT close this window while the system is running.
echo.

:: Change directory to where this .bat file lives (handles drag-and-drop launches)
cd /d "%~dp0"

:: Check if .env exists
if not exist ".env" (
    echo  [WARNING] .env file not found!
    echo  Please create a .env file with your database credentials.
    echo  See README.txt for instructions.
    echo.
    pause
    exit /b 1
)

:: Create required folders if they don't exist yet
if not exist "faces"              mkdir faces
if not exist "uploads"            mkdir uploads
if not exist "uploads\signatures" mkdir uploads\signatures
if not exist "uploads\photos"     mkdir uploads\photos
if not exist "pdf"                mkdir pdf

:: Start the Flask server in the background (keeps this window for logs)
start "" /B AttendanceStation.exe

:: Wait 4 seconds for Flask to boot before opening the browser
echo  Waiting for server to start...
timeout /t 4 /nobreak >nul

:: Open the browser automatically
echo  Opening browser at http://127.0.0.1:5000
start "" "http://127.0.0.1:5000"

echo.
echo  =====================================================
echo   System is RUNNING. Keep this window open.
echo   To stop: close this window or press Ctrl+C
echo  =====================================================
echo.

:: Keep the window alive so the server keeps running and logs are visible
AttendanceStation.exe
