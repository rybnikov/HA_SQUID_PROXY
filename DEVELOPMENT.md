# Development Guide

## Setup

Run the setup script to initialize the development environment:

```bash
./setup_dev.sh
```

Or on Windows:

```powershell
.\setup_dev.ps1
```

## Virtual Environment

Activate the virtual environment:

```bash
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

## Running Tests

Run all tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=custom_components --cov-report=html
```

Run specific test file:

```bash
pytest tests/unit/test_const.py
```

## Code Quality

Format code with Black:

```bash
black custom_components/
```

Lint with Ruff:

```bash
ruff check custom_components/
```

Type checking with mypy:

```bash
mypy custom_components/
```

Run all checks:

```bash
pre-commit run --all-files
```

## Testing with Home Assistant

1. Copy the integration to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration via the UI

## Docker Testing

Build the Docker image:

```bash
docker build -f custom_components/squid_proxy_manager/docker/Dockerfile.scratch -t squid-proxy-manager .
```

## Project Structure

```
SuidManagerHA/
├── custom_components/
│   └── squid_proxy_manager/  # Integration code
├── tests/                    # Test files
├── venv/                     # Virtual environment
├── setup_dev.sh              # Setup script
└── DEVELOPMENT.md           # This file
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Commit with descriptive messages
5. Push and create a pull request
