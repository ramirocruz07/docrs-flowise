#!/bin/bash
echo "Starting Docr Canvas Backend Server..."
echo ""
cd "$(dirname "$0")"
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload








