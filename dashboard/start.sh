#!/bin/bash
"""
Startup script for Garak Dashboard in Cloud Run.
"""

set -e

# Set default port if not specified
export PORT=${PORT:-8080}

# Ensure data directories exist
mkdir -p /app/data /app/reports /app/logs
mkdir -p /home/garak/.config/garak

# Start the application with Gunicorn
echo "Starting Garak Dashboard on port $PORT..."
exec gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 8 \
    --timeout 0 \
    --worker-class gthread \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    app:app