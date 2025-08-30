#!/usr/bin/env python3
"""
Startup script for Wheel Strategy backend
Handles both API and worker modes based on MODE environment variable
"""

import os
import sys
import subprocess

def main():
    mode = os.getenv('MODE', 'api')
    print(f"Starting Wheel Strategy Backend in MODE: {mode}")
    
    if mode == 'worker':
        print("Starting worker...")
        # Import and run the worker
        from worker import main as worker_main
        import asyncio
        asyncio.run(worker_main())
    elif mode == 'api':
        print("Starting API server...")
        # Start uvicorn for the API
        subprocess.run([
            "uvicorn", "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload", 
            "--reload-dir", "/app"
        ])
    else:
        print(f"Unknown MODE: {mode}. Defaulting to API mode.")
        subprocess.run([
            "uvicorn", "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload", 
            "--reload-dir", "/app"
        ])

if __name__ == "__main__":
    main()
