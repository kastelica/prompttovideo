# Gunicorn configuration for memory optimization

# Worker settings
workers = 1  # Use single worker to minimize memory usage
worker_class = "sync"
worker_connections = 500  # Reduce connections
max_requests = 500  # Restart workers more frequently to prevent memory leaks
max_requests_jitter = 25
preload_app = True  # Share memory between workers

# Timeout settings
timeout = 120
keepalive = 60

# Memory optimization
worker_tmp_dir = "/dev/shm"  # Use RAM for temporary files

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Server socket
bind = "0.0.0.0:8080"

# Performance tuning
worker_rlimit_nofile = 1024
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def on_exit(server):
    server.log.info("Server is shutting down")