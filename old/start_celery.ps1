# Start Celery Worker for PromptToVideo
Write-Host "🚀 Starting Celery Worker for PromptToVideo..." -ForegroundColor Green

# Activate virtual environment if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "📦 Activating virtual environment..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
}

# Start Celery worker
Write-Host "🔧 Starting Celery worker..." -ForegroundColor Yellow
Write-Host "📝 Note: Use Ctrl+C to stop the worker" -ForegroundColor Cyan
celery -A app.tasks.celery worker --loglevel=info --pool=solo 