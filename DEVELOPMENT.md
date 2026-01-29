# Development Guide: HA Squid Proxy Manager

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- `pre-commit`
- Node.js (for Playwright local testing, optional)

## Setup Development Environment

1.  **Clone the repository**
2.  **Run the setup script**:
    ```bash
    ./setup_dev.sh
    ```
    This script will:
    - Create a Python virtual environment.
    - Install all necessary dependencies (`pytest`, `ruff`, `black`, `mypy`, `bandit`, `safety`).
    - Install `pre-commit` hooks.
    - Set up a basic configuration for local testing.

## Project Structure

- `squid_proxy_manager/rootfs/app/`: Core logic.
- `tests/unit/`: Component-level tests.
- `tests/integration/`: Process-based tests with mocked Squid.
- `tests/e2e/`: Full Docker-based traffic and UI tests.

## Code Quality & Security

We use `pre-commit` to ensure code quality and security before every commit.

### Manual Checks
```bash
# Run all linters and security checks
pre-commit run --all-files

# Specific tools
ruff check .
black .
mypy .
bandit -c pyproject.toml -r .
safety check
```

## Testing

### Local Tests (Unit & Integration)
```bash
./run_tests.sh
```

### E2E Tests (Docker-based)
These tests run the full add-on in a container and perform traffic and UI validation.
```bash
docker compose -f docker-compose.test.yaml up --build --exit-code-from tester
```

## Troubleshooting

### Logs
Squid logs are located in `/data/squid_proxy_manager/logs/<instance>/`.
In the Web UI, use the **Logs** button to view them in real-time.

### Common Issues
- **Port Conflict**: Ensure the port you assigned to an instance is not used by another instance or the Home Assistant host.
- **Permission Denied**: The add-on requires write access to `/data`.
