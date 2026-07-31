@echo off
echo ========================================
echo   SOCKS5 Proxy Server - Starting...
echo ========================================
start "Flask API" cmd /k "cd /d %~dp0 && python run.py"
start "Dante SOCKS5" cmd /k "C:\dante\sockd.exe -f C:\dante\sockd.conf"
echo Flask API  → http://localhost:5000
echo Dashboard  → http://localhost:5000/dashboard
echo SOCKS5     → port 10800
pause
