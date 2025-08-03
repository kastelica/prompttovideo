# Manual Redis Setup for PromptToVideo

Since the automated setup scripts are having issues, here's a manual approach:

## Option 1: Download Redis for Windows

1. **Download Redis for Windows**:
   - Go to: https://github.com/microsoftarchive/redis/releases
   - Download the latest release (e.g., `Redis-x64-3.0.504.msi`)

2. **Install Redis**:
   - Run the downloaded MSI file
   - Follow the installation wizard
   - Make sure to check "Add to PATH" during installation

3. **Start Redis**:
   ```powershell
   # Start Redis server
   redis-server
   
   # In another terminal, test the connection
   redis-cli ping
   ```

## Option 2: Use Windows Subsystem for Linux (WSL)

If you have WSL installed:

1. **Install Redis in WSL**:
   ```bash
   sudo apt update
   sudo apt install redis-server
   sudo systemctl start redis-server
   sudo systemctl enable redis-server
   ```

2. **Test Redis**:
   ```bash
   redis-cli ping
   ```

3. **Update your .env file**:
   ```
   REDIS_URL=redis://localhost:6379/0
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```

## Option 3: Use Docker (Recommended for Development)

1. **Install Docker Desktop**:
   - Download from: https://www.docker.com/products/docker-desktop
   - Install and start Docker Desktop

2. **Run Redis in Docker**:
   ```bash
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   ```

3. **Test Redis**:
   ```bash
   docker exec -it redis redis-cli ping
   ```

## Option 4: Skip Redis for Now (Use Direct Execution)

If you want to test the video generation without Redis:

1. **The system will automatically fall back to direct execution**
2. **No Redis setup required**
3. **Videos will still generate, just synchronously**

## Testing Your Setup

Once Redis is running, test it:

```powershell
# Test Redis connection
redis-cli ping
# Should return: PONG

# Test with Python
python -c "import redis; r = redis.Redis(); print(r.ping())"
# Should return: True
```

## Starting Celery Worker

After Redis is running:

```powershell
# Start Celery worker
celery -A app.tasks.celery worker --loglevel=info --pool=solo
```

## Starting Flask App

In another terminal:

```powershell
python run.py
```

## Troubleshooting

### Redis Connection Issues
- Make sure Redis is running: `redis-cli ping`
- Check if port 6379 is available: `netstat -an | findstr 6379`
- Try different Redis URL: `redis://127.0.0.1:6379/0`

### Celery Issues
- Check if Redis is accessible: `celery -A app.tasks.celery inspect ping`
- Clear Celery cache: `celery -A app.tasks.celery purge`
- Check registered tasks: `celery -A app.tasks.celery inspect registered` 