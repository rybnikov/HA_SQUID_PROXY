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

format_duration() {
    local total=$1
    local mins=$((total / 60))
    local secs=$((total % 60))
    printf "%02dm%02ds" "$mins" "$secs"
}

detect_platform_defaults() {
    local arch
    arch="$(uname -m)"
    case "$arch" in
        arm64|aarch64)
            BUILD_ARCH="aarch64"
            DOCKER_PLATFORM="linux/arm64"
            ;;
        x86_64|amd64)
            BUILD_ARCH="amd64"
            DOCKER_PLATFORM="linux/amd64"
            ;;
        armv7l|armv7)
            BUILD_ARCH="armv7"
            DOCKER_PLATFORM="linux/arm/v7"
            ;;
        armv6l|armv6)
            BUILD_ARCH="armhf"
            DOCKER_PLATFORM="linux/arm/v6"
            ;;
        i386|i686)
            BUILD_ARCH="i386"
            DOCKER_PLATFORM="linux/386"
            ;;
        *)
            print_warning "Unknown architecture '$arch'. Set BUILD_ARCH and DOCKER_PLATFORM explicitly."
            ;;
    esac
}

ensure_platform_env() {
    if [ -z "${BUILD_ARCH:-}" ] || [ -z "${DOCKER_PLATFORM:-}" ]; then
        detect_platform_defaults
    fi

    if [ -n "${BUILD_ARCH:-}" ]; then
        export BUILD_ARCH
    fi

    if [ -n "${DOCKER_PLATFORM:-}" ]; then
        export DOCKER_PLATFORM
        if [ -z "${DOCKER_DEFAULT_PLATFORM:-}" ]; then
            export DOCKER_DEFAULT_PLATFORM="$DOCKER_PLATFORM"
        fi
    fi
}

# Default to Docker mode
MODE="${1:-all}"

if [ "$MODE" != "local" ] && [ "$MODE" != "help" ] && [ "$MODE" != "--help" ] && [ "$MODE" != "-h" ]; then
    ensure_platform_env
fi

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
            START_TIME=$(date +%s)
            pytest tests/unit tests/integration -v --tb=short \
                --cov=squid_proxy_manager/rootfs/app \
                --cov-report=term-missing \
                --cov-report=html
            END_TIME=$(date +%s)
            print_status "Local unit+integration duration: $(format_duration $((END_TIME - START_TIME)))"
        else
            START_TIME=$(date +%s)
            pytest "$@" -v --tb=short \
                --cov=squid_proxy_manager/rootfs/app \
                --cov-report=term-missing \
                --cov-report=html
            END_TIME=$(date +%s)
            print_status "Local tests duration: $(format_duration $((END_TIME - START_TIME)))"
        fi
        ;;

    unit|integration)
        # Run unit + integration tests in Docker (no addon needed)
        print_status "Running unit + integration tests in Docker..."
        START_TIME=$(date +%s)
        docker compose -f docker-compose.test.yaml --profile unit build test-runner
        docker compose -f docker-compose.test.yaml --profile unit run --rm test-runner
        END_TIME=$(date +%s)
        print_status "Unit+integration duration: $(format_duration $((END_TIME - START_TIME)))"
        ;;

    ui)
        # Run frontend lint/typecheck/unit tests in Docker
        print_status "Running frontend checks in Docker..."
        START_TIME=$(date +%s)
        docker compose -f docker-compose.test.yaml --profile ui build ui-runner
        docker compose -f docker-compose.test.yaml --profile ui run --rm ui-runner
        END_TIME=$(date +%s)
        print_status "UI checks duration: $(format_duration $((END_TIME - START_TIME)))"
        ;;

    e2e)
        # Run E2E tests in Docker with addon
        print_status "Building and starting addon for E2E tests..."
        START_TIME=$(date +%s)
        docker compose -f docker-compose.test.yaml --profile e2e build
        set +e
        docker compose -f docker-compose.test.yaml --profile e2e up --abort-on-container-exit --exit-code-from e2e-runner
        E2E_STATUS=$?
        set -e
        docker compose -f docker-compose.test.yaml --profile e2e down -v
        END_TIME=$(date +%s)
        print_status "E2E duration: $(format_duration $((END_TIME - START_TIME)))"
        if [ $E2E_STATUS -ne 0 ]; then
            print_error "E2E tests failed"
            exit $E2E_STATUS
        fi
        ;;

    all|docker)
        # Run all tests in Docker
        print_status "Running ALL tests in Docker (unit + integration + e2e)..."
        TOTAL_START=$(date +%s)

        # First run unit + integration tests
        print_status "Phase 1: Unit + Integration tests (parallel with UI checks)..."
        docker compose -f docker-compose.test.yaml --profile unit --profile ui build --parallel test-runner ui-runner
        UNIT_TIMING_FILE=$(mktemp)
        UI_TIMING_FILE=$(mktemp)

        (
            UNIT_START=$(date +%s)
            docker compose -f docker-compose.test.yaml --profile unit run --rm test-runner
            UNIT_STATUS=$?
            UNIT_END=$(date +%s)
            echo "$UNIT_STATUS $((UNIT_END - UNIT_START))" > "$UNIT_TIMING_FILE"
        ) &
        UNIT_PID=$!

        (
            UI_START=$(date +%s)
            docker compose -f docker-compose.test.yaml --profile ui run --rm ui-runner
            UI_STATUS=$?
            UI_END=$(date +%s)
            echo "$UI_STATUS $((UI_END - UI_START))" > "$UI_TIMING_FILE"
        ) &
        UI_PID=$!

        set +e
        wait $UNIT_PID
        wait $UI_PID
        set -e

        read -r UNIT_STATUS UNIT_DURATION < "$UNIT_TIMING_FILE"
        read -r UI_STATUS UI_DURATION < "$UI_TIMING_FILE"
        rm -f "$UNIT_TIMING_FILE" "$UI_TIMING_FILE"

        print_status "Phase 1 duration: unit+integration=$(format_duration "$UNIT_DURATION"), ui=$(format_duration "$UI_DURATION")"

        if [ "$UNIT_STATUS" -ne 0 ] || [ "$UI_STATUS" -ne 0 ]; then
            print_error "Unit/Integration or UI tests failed"
            exit 1
        fi

        # Then run E2E tests with addon
        print_status "Phase 3: E2E tests with real Squid..."
        E2E_START=$(date +%s)
        docker compose -f docker-compose.test.yaml --profile e2e build
        set +e
        docker compose -f docker-compose.test.yaml --profile e2e up --abort-on-container-exit --exit-code-from e2e-runner
        E2E_STATUS=$?
        set -e
        docker compose -f docker-compose.test.yaml --profile e2e down -v
        E2E_END=$(date +%s)
        print_status "Phase 3 duration: e2e=$(format_duration $((E2E_END - E2E_START)))"

        if [ $E2E_STATUS -ne 0 ]; then
            print_error "E2E tests failed"
            exit $E2E_STATUS
        fi

        TOTAL_END=$(date +%s)
        print_status "Total duration: $(format_duration $((TOTAL_END - TOTAL_START)))"
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
