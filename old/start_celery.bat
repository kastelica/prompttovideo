@echo off
echo 🚀 Starting Celery Worker for PromptToVideo...
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo 📦 Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start Celery worker
echo 🔧 Starting Celery worker...
celery -A app.tasks.celery worker --loglevel=info --pool=solo

echo.
echo Celery worker stopped. Press any key to exit...
pause > nul 