@echo off
echo ============================================================
echo PRAYER SCHEDULE UPDATE - VERSION 10 (DESKTOP) - FIXED
echo ============================================================
echo.
echo This will update the prayer schedule files on your desktop.
echo.

REM FIXED: Use %USERPROFILE% environment variable instead of hard-coded path
cd /d "%USERPROFILE%\Desktop"

REM Check if Python script exists
if not exist prayer_schedule_V10_DESKTOP_FIXED.py (
    echo ERROR: Cannot find prayer_schedule_V10_DESKTOP_FIXED.py on the desktop!
    echo Please make sure the Python script is on your desktop.
    pause
    exit /b 1
)

REM Run the Python script
python prayer_schedule_V10_DESKTOP_FIXED.py

REM Check if Python ran successfully
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: The Python script encountered an error.
    echo Please check the error messages above.
) else (
    echo.
    echo ============================================================
    echo Update complete! All files are saved on your desktop.
    echo ============================================================
)

pause
