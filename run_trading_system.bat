rem filepath: c:\WORK\kis-scalper\run_trading_system.bat
@echo off
echo ==========================================
echo    KIS Scalping System v6.0 Start
echo ==========================================

REM Activate virtual environment (if any)
REM call venv\Scripts\activate

REM Check Python path
python --version
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Install required packages
echo Checking for required packages...
pip install -r requirements.txt -q

REM Create log directory
if not exist logs mkdir logs

REM Run main system
echo.
echo Starting Integrated Trading System...
echo Press Ctrl+C to exit.
echo.

python main_integrated.py

REM Display logs after exit
echo.
echo ==========================================
echo           System Shut Down
echo ==========================================
echo Check log files in: logs\
echo Performance Report: logs\daily_report_*.txt
echo Backtest Result: logs\backtest_result_*.json
echo.
pause