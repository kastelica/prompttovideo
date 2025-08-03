# Setup Redis for PromptToVideo
# This script installs Redis using Chocolatey and starts the Redis service

Write-Host "Setting up Redis for PromptToVideo..." -ForegroundColor Green

# Check if Chocolatey is installed
if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Chocolatey is not installed. Installing Chocolatey..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Host "Chocolatey installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Chocolatey is already installed" -ForegroundColor Green
}

# Install Redis
Write-Host "Installing Redis..." -ForegroundColor Yellow
choco install redis-64 -y

# Start Redis service
Write-Host "Starting Redis service..." -ForegroundColor Yellow
Start-Service redis

# Set Redis to start automatically on boot
Write-Host "Setting Redis to start automatically..." -ForegroundColor Yellow
Set-Service redis -StartupType Automatic

# Test Redis connection
Write-Host "Testing Redis connection..." -ForegroundColor Yellow
try {
    redis-cli ping
    Write-Host "Redis is running successfully!" -ForegroundColor Green
} catch {
    Write-Host "Failed to connect to Redis. Please check the installation." -ForegroundColor Red
    exit 1
}

Write-Host "Redis setup complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "   1. Start your Flask application" -ForegroundColor White
Write-Host "   2. Start Celery worker: celery -A app.tasks.celery worker --loglevel=info" -ForegroundColor White
Write-Host "   3. Generate videos and check the dashboard for progress!" -ForegroundColor White 