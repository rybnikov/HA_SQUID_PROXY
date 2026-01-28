# Development Guide

## Requirements

Before setting up the development environment, ensure you have:

1. **Python 3.10+** - Required for running the application
2. **Docker** - **REQUIRED** for integration tests
   - Install Docker: https://docs.docker.com/get-docker/
   - Ensure Docker daemon is running
   - Verify with: `docker ps`

## Setup

Run the setup script to initialize the development environment:

```bash
./setup_dev.sh
```

The setup script will:
- Verify Python 3.10+ is installed
- Verify Docker is installed and running
- Create a Python virtual environment
- Install all dependencies
- Set up pre-commit hooks

**Note:** The setup will FAIL if Docker is not installed and running.

## Virtual Environment

Activate the virtual environment:

```bash
source venv/bin/activate  # Linux/macOS
```

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Integration Tests (requires Docker)
```bash
pytest tests/integration/ -v
```

### Specific Test Files
```bash
# Docker integration tests
pytest tests/integration/test_docker_integration.py -v

# Ingress compatibility tests
pytest tests/integration/test_ingress_compatibility.py -v

# Server startup tests
pytest tests/integration/test_server_startup.py -v
```

### With Coverage
```bash
pytest --cov=squid_proxy_manager --cov-report=html
```

## Test Categories

### Unit Tests (`tests/unit/`)
- Do not require Docker
- Test individual components in isolation
- Fast execution

### Integration Tests (`tests/integration/`)

#### Docker Integration Tests (`test_docker_integration.py`)
- **REQUIRE Docker to be running**
- Test real Docker connectivity
- Test ProxyInstanceManager with real containers
- Will FAIL (not skip) if Docker is unavailable

#### Ingress Compatibility Tests (`test_ingress_compatibility.py`)
- Test HTTP server behavior
- Test path normalization
- Test API endpoints
- Test concurrent requests

#### Server Startup Tests (`test_server_startup.py`)
- Test application startup flow
- Test error handling

## Code Quality

Format code with Black:
```bash
black squid_proxy_manager/
```

Lint with Ruff:
```bash
ruff check squid_proxy_manager/
```

Run all checks:
```bash
pre-commit run --all-files
```

## Building the Addon

Build the Docker image locally:
```bash
cd squid_proxy_manager
docker build -t squid-proxy-manager:local .
```

## Project Structure

```
HA_SQUID_PROXY/
├── squid_proxy_manager/        # Addon code
│   ├── rootfs/                 # Files copied to container
│   │   ├── app/                # Python application
│   │   │   ├── main.py         # Main entry point
│   │   │   ├── proxy_manager.py
│   │   │   └── ...
│   │   └── etc/                # s6-overlay services
│   ├── Dockerfile              # Addon Dockerfile
│   └── config.yaml             # Addon configuration
├── tests/                      # Test files
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── venv/                       # Virtual environment
├── setup_dev.sh                # Setup script
└── DEVELOPMENT.md              # This file
```

## Troubleshooting

### Docker not running
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

### Permission denied for Docker socket
```bash
sudo usermod -aG docker $USER
# Then log out and back in
```

### Tests failing with "Docker not available"
Ensure Docker is running:
```bash
docker ps
docker run --rm hello-world
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `pytest`
4. Run linting: `pre-commit run --all-files`
5. Commit with descriptive messages
6. Push and create a pull request
