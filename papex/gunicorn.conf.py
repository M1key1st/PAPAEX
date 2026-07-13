"""Gunicorn configuration for PAPEX production deployment."""

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Restart workers after this many requests (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "papex"

# Server mechanics
preload_app = True
daemon = False

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# SSL (optional, if not using nginx)
# certfile = "/path/to/cert.pem"
# keyfile = "/path/to/key.pem"
