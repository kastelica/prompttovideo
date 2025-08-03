# Redis and Celery Setup for PromptToVideo

This guide will help you set up Redis and Celery for background video processing.

## Quick Setup (Windows)

### 1. Install Redis using Chocolatey

Run the setup script:
```bash
# Option 1: Using PowerShell
powershell -ExecutionPolicy Bypass -File "setup_redis.ps1"

# Option 2: Using batch file
setup_redis.bat
```

Or manually:
```bash
# Install Chocolatey (if not already installed)
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Redis
choco install redis-64 -y

# Start Redis service
Start-Service redis
Set-Service redis -StartupType Automatic
```

### 2. Start Celery Worker

In a new terminal window:
```bash
# Option 1: Using PowerShell
powershell -ExecutionPolicy Bypass -File "start_celery.ps1"

# Option 2: Using batch file
start_celery.bat

# Option 3: Manual command
celery -A app.tasks.celery worker --loglevel=info --pool=solo
```

### 3. Start Flask Application

In another terminal window:
```bash
python run.py
# or
flask run
```

## How It Works

### Before (Synchronous Processing)
1. User clicks "Generate Video"
2. Frontend waits for entire video generation to complete
3. User sees loading spinner for 2-3 minutes
4. Page redirects to dashboard when complete

### After (Asynchronous Processing)
1. User clicks "Generate Video"
2. Backend immediately queues the task and returns
3. Frontend shows "Video generation queued successfully"
4. User is redirected to dashboard after 2 seconds
5. Video processes in background via Celery worker
6. User can see progress on dashboard

## Benefits

- **Better UX**: No more hanging on the frontend
- **Scalability**: Multiple videos can be processed simultaneously
- **Reliability**: Failed tasks can be retried
- **Monitoring**: Queue status and progress tracking

## Troubleshooting

### Redis Connection Issues
```bash
# Test Redis connection
redis-cli ping
# Should return: PONG

# Check Redis service status
Get-Service redis
```

### Celery Worker Issues
```bash
# Check if Celery can connect to Redis
celery -A app.tasks.celery inspect ping

# Check active tasks
celery -A app.tasks.celery inspect active

# Check registered tasks
celery -A app.tasks.celery inspect registered
```

### Environment Variables
Make sure these are set in your `.env` file:
```
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Development vs Production

### Development
- Uses `--pool=solo` for Windows compatibility
- Single worker process
- Local Redis instance

### Production
- Use `--pool=prefork` for better performance
- Multiple worker processes
- Redis cluster or cloud Redis service
- Monitor with Flower: `celery -A app.tasks.celery flower`

## Queue Management

### Check Queue Status
```bash
# API endpoint (requires authentication)
GET /api/queue/status

# Celery command
celery -A app.tasks.celery inspect stats
```

### Clear Queue
```bash
# Clear all pending tasks
celery -A app.tasks.celery purge
```

### Monitor Tasks
```bash
# Watch task progress
celery -A app.tasks.celery events
``` 