#!/bin/bash
# Run tests in Docker (recommended) or locally
#
# Usage:
#   ./run_tests.sh                  # Run all tests in Docker (unit + integration + e2e)
#   ./run_tests.sh unit             # Run only unit + integration tests in Docker
#   ./run_tests.sh ui               # Run frontend lint/typecheck/unit tests in Docker
#   ./run_tests.sh e2e              # Run only E2E tests in Docker (with addon)
#   ./run_tests.sh local [args]     # Run tests locally (some may be skipped due to sandbox)
#
# Examples:
#   ./run_tests.sh                  # Full test suite in Docker
#   ./run_tests.sh unit             # Quick unit/integration tests
#   ./run_tests.sh ui               # Frontend checks
#   ./run_tests.sh e2e              # E2E with real Squid
#   ./run_tests.sh local tests/unit # Run unit tests locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}==>${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

print_error() {
    echo -e "${RED}Error:${NC} $1"
}

# Default to Docker mode
MODE="${1:-all}"

case "$MODE" in
    local)
        # Run tests locally (some may be skipped due to sandbox)
        shift
        print_warning "Running locally - some tests may be skipped due to sandbox restrictions"

        if [ -d "venv" ]; then
            source venv/bin/activate
        fi

        # Default to unit + integration if no args
        if [ $# -eq 0 ]; then
            pytest tests/unit tests/integration -v --tb=short \
                --cov=squid_proxy_manager/rootfs/app \
                --cov-report=term-missing \
                --cov-report=html
        else
            pytest "$@" -v --tb=short \
                --cov=squid_proxy_manager/rootfs/app \
                --cov-report=term-missing \
                --cov-report=html
        fi
        ;;

    unit|integration)
        # Run unit + integration tests in Docker (no addon needed)
        print_status "Running unit + integration tests in Docker..."
        docker compose -f docker-compose.test.yaml --profile unit build test-runner
        docker compose -f docker-compose.test.yaml --profile unit run --rm test-runner
        ;;

    ui)
        # Run frontend lint/typecheck/unit tests in Docker
        print_status "Running frontend checks in Docker..."
        docker compose -f docker-compose.test.yaml --profile ui build ui-runner
        docker compose -f docker-compose.test.yaml --profile ui run --rm ui-runner
        ;;

    e2e)
        # Run E2E tests in Docker with addon
        print_status "Building and starting addon for E2E tests..."
        docker compose -f docker-compose.test.yaml --profile e2e build
        docker compose -f docker-compose.test.yaml --profile e2e up --abort-on-container-exit --exit-code-from e2e-runner
        docker compose -f docker-compose.test.yaml --profile e2e down -v
        ;;

    all|docker)
        # Run all tests in Docker
        print_status "Running ALL tests in Docker (unit + integration + e2e)..."

        # First run unit + integration tests
        print_status "Phase 1: Unit + Integration tests..."
        docker compose -f docker-compose.test.yaml --profile unit build test-runner
        docker compose -f docker-compose.test.yaml --profile unit run --rm test-runner

        print_status "Phase 2: Frontend lint/typecheck/unit tests..."
        docker compose -f docker-compose.test.yaml --profile ui build ui-runner
        docker compose -f docker-compose.test.yaml --profile ui run --rm ui-runner

        # Then run E2E tests with addon
        print_status "Phase 3: E2E tests with real Squid..."
        docker compose -f docker-compose.test.yaml --profile e2e build
        docker compose -f docker-compose.test.yaml --profile e2e up --abort-on-container-exit --exit-code-from e2e-runner
        docker compose -f docker-compose.test.yaml --profile e2e down -v

        print_status "All tests completed successfully!"
        ;;

    help|--help|-h)
        echo "Run tests in Docker (recommended) or locally"
        echo ""
        echo "Usage:"
        echo "  ./run_tests.sh                  # Run all tests in Docker"
        echo "  ./run_tests.sh unit             # Run unit + integration tests in Docker"
        echo "  ./run_tests.sh ui               # Run frontend lint/typecheck/unit tests in Docker"
        echo "  ./run_tests.sh e2e              # Run E2E tests in Docker (with addon)"
        echo "  ./run_tests.sh local [args]     # Run tests locally (some skipped)"
        echo ""
        echo "Docker mode runs with full network access - no tests skipped."
        echo "Local mode may skip tests due to sandbox restrictions."
        ;;

    *)
        print_error "Unknown mode: $MODE"
        echo "Use './run_tests.sh help' for usage"
        exit 1
        ;;
esac
