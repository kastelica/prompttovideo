@echo off
echo 🚀 Setting up Redis for PromptToVideo...
echo.

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "setup_redis.ps1"

echo.
echo Setup complete! Press any key to exit...
pause > nul 