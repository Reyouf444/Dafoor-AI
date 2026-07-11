#!/bin/bash

# Exit on error
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================================="
echo "               Starting Dafoor AI Server Setup            "
echo "=========================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed." >&2
    exit 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Error: venv directory not found. Please verify setup steps." >&2
    exit 1
fi

# Ensure requirements are updated
echo "Verifying backend dependencies..."
pip install --disable-pip-version-check -r backend/requirements.txt

# Initializing directories and DB test
echo "Verifying SQLite database tables structure..."
python3 -c "
import sys
sys.path.append('$PROJECT_DIR')
from backend.database import init_db
init_db()
print('Database initialized successfully.')
"

echo "----------------------------------------------------------"
echo "  Server starting at: http://127.0.0.1:8000"
echo "  Open this link in your web browser to access the app.   "
echo "  To shut down, press [CTRL+C] in this terminal.          "
echo "----------------------------------------------------------"

# Launch application
exec uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
