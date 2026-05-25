@echo off
cd /d C:\Applio
set PYTHONUNBUFFERED=1
echo Starting Applio at http://127.0.0.1:6969
echo Keep this window open while using Applio.
C:\Applio\env\python.exe C:\Applio\app.py --server-name 127.0.0.1 --port 6969
echo.
echo Applio stopped. Press any key to close this window.
pause >nul
