#!/bin/bash
set -e

# Load environment variables and export them
set -a  # automatically export all variables
source .env
set +a  # stop automatically exporting

# Set default host and port
HOST="127.0.0.1"
PORT="8000"

# Launch uvicorn
poetry run uvicorn app.main:app --host $HOST --port $PORT --reload