#!/bin/bash
# Helper script to run tests

set -e

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run tests
pytest tests/ -v --tb=short "$@"
