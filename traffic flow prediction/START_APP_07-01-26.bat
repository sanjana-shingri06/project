@echo off
REM Traffic Flow Prediction - Startup Script
REM Run this file to start the project automatically

cd /d "C:\Users\sanja\Desktop\traffic flow prediction"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start the Flask app
echo.
echo ====================================================
echo    Traffic Flow Prediction Application
echo ====================================================
echo.
echo Server starting on http://127.0.0.1:5000/
echo.
echo Open in your browser:
echo   - Map: http://127.0.0.1:5000/map
echo.
echo Press Ctrl+C to stop the server
echo ====================================================
echo.

python app.py
pause
