#!/bin/bash
# Helper script to run tests

set -e

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run tests
pytest tests/unit tests/integration -v --tb=short --cov=squid_proxy_manager/rootfs/app --cov-report=term-missing --cov-report=html "$@"
