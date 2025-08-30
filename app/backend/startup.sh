#!/bin/bash

# Startup script for Wheel Strategy backend
# Handles both API and worker modes based on MODE environment variable

set -e

echo "Starting Wheel Strategy Backend in MODE: ${MODE:-api}"

case "${MODE:-api}" in
    "api")
        echo "Starting API server..."
        exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app
        ;;
    "worker")
        echo "Starting worker..."
        exec python worker.py
        ;;
    *)
        echo "Unknown MODE: ${MODE}. Defaulting to API mode."
        exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app
        ;;
esac
