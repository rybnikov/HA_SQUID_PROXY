"""Pytest configuration and fixtures."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_docker_client():
    """Mock Docker client."""
    client = MagicMock()
    client.ping.return_value = True

    # Mock containers
    containers: list[MagicMock] = []
    client.containers.list.return_value = containers

    def get_container(name):
        for c in containers:
            if c.name == name:
                return c
        raise Exception(f"Container {name} not found")

    client.containers.get.side_effect = get_container

    return client


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_instance_config():
    """Sample instance configuration."""
    return {
        "name": "test-instance",
        "port": 3128,
        "https_enabled": False,
        "users": [
            {"username": "user1", "password": "password123"},  # pragma: allowlist secret
            {"username": "user2", "password": "password456"},  # pragma: allowlist secret
        ],
    }
