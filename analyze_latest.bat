@echo off
REM Mind Monitor Analysis Automation
REM Double-click to import from Google Drive and analyze latest recording

cd /d "C:\dev\musepython"
call venv\Scripts\activate.bat

echo ============================================================
echo MIND MONITOR AUTOMATIC ANALYSIS (GOOGLE DRIVE)
echo ============================================================
echo.

REM Import latest file from Google Drive
echo [1/3] Importing latest Mind Monitor file from Google Drive...
echo.
python gdrive_mindmonitor_importer.py
if errorlevel 1 (
    echo.
    echo ERROR: Import failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [2/3] Finding latest recording...
echo.

REM Find the most recent Mind Monitor CSV (exclude AI insights files)
for /f "delims=" %%i in ('dir /b /od /s recordings\2025-*\muse_mindmonitor_*.csv 2^>nul ^| findstr /v "ai_insights"') do set latest=%%i

if "%latest%"=="" (
    echo No Mind Monitor recordings found.
    echo.
    echo Please check Google Drive authentication
    pause
    exit /b 1
)

echo Found: %latest%
echo.

echo ============================================================
echo [3/3] Running AI Analysis with LM Studio...
echo ============================================================
echo.

python muse_ai_analyzer.py "%latest%"
if errorlevel 1 (
    echo.
    echo ERROR: Analysis failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ANALYSIS COMPLETE!
echo ============================================================
echo.
echo Results saved alongside CSV file:
echo   - .ai_insights.txt (AI analysis)
echo   - .metadata.json (session info)
echo.
echo To visualize: python muse_visualizer.py "%latest%"
echo.
pause
