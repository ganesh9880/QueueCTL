@echo off
echo ============================================
echo Starting queuectl Web UI...
echo ============================================
echo.
echo Server will start at: http://127.0.0.1:5000
echo.
echo Opening browser in 3 seconds...
echo.
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5000
echo.
echo Starting web server...
echo Press Ctrl+C to stop the server
echo.
python -m queuectl.cli web

