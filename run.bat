@echo off
echo ============================================================
echo   Hospital Patient Queue Management System
echo   OS Concepts: Priority Scheduling + Aging + Semaphores
echo ============================================================
echo.
echo Starting server at http://127.0.0.1:5000
echo Press Ctrl+C to stop.
echo.
cd /d "%~dp0"
.venv\Scripts\python.exe main.py
pause
