#!/usr/bin/env python
"""
Startup script for Render deployment.
Runs migrations, collects static files, then starts gunicorn.
"""
import os
import sys
import subprocess

def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"\n==> {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=False)
    if result.returncode != 0:
        print(f"ERROR: {description} failed with code {result.returncode}")
        sys.exit(result.returncode)
    print(f"✓ {description} completed successfully")

if __name__ == "__main__":
    # Get PORT from environment
    port = os.environ.get("PORT", "8000")
    
    # Run migrations
    run_command(
        "python manage.py migrate --noinput --run-syncdb",
        "Running database migrations"
    )
    
    # Collect static files
    run_command(
        "python manage.py collectstatic --noinput",
        "Collecting static files"
    )
    
    # Start gunicorn
    print(f"\n==> Starting gunicorn on port {port}...")
    os.execvp("gunicorn", [
        "gunicorn",
        "config.wsgi:application",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "4",
        "--timeout", "120",
        "--log-level", "info"
    ])
