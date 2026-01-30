"""
Gunicorn configuration file for NOC RAG POC
"""
import multiprocessing
import os

# Bind address
bind = "127.0.0.1:8000"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000

# Timeouts
timeout = 120  # 2 minutes (karena DeepSeek API bisa lama)
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "noc_rag"

# Server mechanics
daemon = False
preload_app = True  # Load application code before worker processes are forked
max_requests = 1000  # Restart workers after this many requests (prevent memory leaks)
max_requests_jitter = 50  # Randomize restart to prevent all workers restarting at once

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
