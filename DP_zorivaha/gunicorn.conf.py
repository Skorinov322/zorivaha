"""
gunicorn.conf.py — Gunicorn configuration for production.

Usage:
    gunicorn config.wsgi:application -c gunicorn.conf.py
"""

import multiprocessing
import os

# ── Binding ───────────────────────────────────────────────────────────────────
# Use Unix socket when behind Nginx (faster than TCP)
bind = os.getenv("GUNICORN_BIND", "unix:/run/gunicorn/zorivaha.sock")

# ── Workers ───────────────────────────────────────────────────────────────────
# Rule of thumb: (2 × CPU cores) + 1
workers     = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
threads     = 1                 # sync worker: 1 thread per worker
worker_connections = 1000

# ── Timeouts ──────────────────────────────────────────────────────────────────
timeout      = 120              # kill worker if silent for 120s
keepalive    = 5                # keep connection alive for 5s
graceful_timeout = 30           # wait 30s for workers to finish on reload

# ── Requests ──────────────────────────────────────────────────────────────────
max_requests        = 1000      # restart worker after N requests (memory leak guard)
max_requests_jitter = 100       # add random jitter to avoid thundering herd

# ── Logging ───────────────────────────────────────────────────────────────────
loglevel      = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'
accesslog     = "-"             # stdout
errorlog      = "-"             # stderr
capture_output = True           # capture Django print() to error log

# ── Process ───────────────────────────────────────────────────────────────────
proc_name     = "zorivaha"
pidfile       = "/run/gunicorn/zorivaha.pid"
user          = os.getenv("GUNICORN_USER",  "zorivaha")
group         = os.getenv("GUNICORN_GROUP", "zorivaha")
umask         = 0o007

# ── Security ──────────────────────────────────────────────────────────────────
limit_request_line   = 8190
limit_request_fields = 100
forwarded_allow_ips  = "*"      # trust X-Forwarded-For from Nginx

# ── Hooks ─────────────────────────────────────────────────────────────────────
def on_starting(server):
    server.log.info("Зори Ваха — Gunicorn starting")

def worker_exit(server, worker):
    server.log.info(f"Worker {worker.pid} exited")

def post_fork(server, worker):
    """Called after worker fork — close any inherited DB connections."""
    from django.db import connections
    for conn in connections.all():
        conn.close()
