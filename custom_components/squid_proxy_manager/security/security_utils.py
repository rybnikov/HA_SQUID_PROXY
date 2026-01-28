"""Security utilities for file permissions, validation, and security best practices."""
from __future__ import annotations

import logging
import os
import re
import stat
from pathlib import Path
from typing import Any

from ..const import (
    MIN_PORT,
    MAX_PORT,
    SYSTEM_PORTS_WARNING,
    MIN_PASSWORD_LENGTH,
    PERM_CONFIG_FILE,
    PERM_DIRECTORY,
    PERM_PRIVATE_KEY,
    PERM_PASSWORD_FILE,
)

_LOGGER = logging.getLogger(__name__)


def set_file_permissions(file_path: Path, mode: int) -> None:
    """Set file permissions securely.

    Args:
        file_path: Path to the file
        mode: Permission mode (e.g., 0o600)
    """
    try:
        os.chmod(file_path, mode)
        _LOGGER.debug("Set permissions %o on %s", mode, file_path)
    except OSError as ex:
        _LOGGER.error("Failed to set permissions on %s: %s", file_path, ex)
        raise


def set_directory_permissions(dir_path: Path, mode: int = PERM_DIRECTORY) -> None:
    """Set directory permissions securely.

    Args:
        dir_path: Path to the directory
        mode: Permission mode (default: 0o755)
    """
    try:
        os.chmod(dir_path, mode)
        _LOGGER.debug("Set permissions %o on directory %s", mode, dir_path)
    except OSError as ex:
        _LOGGER.error("Failed to set permissions on directory %s: %s", dir_path, ex)
        raise


def ensure_secure_directory(dir_path: Path) -> None:
    """Ensure a directory exists with secure permissions.

    Args:
        dir_path: Path to the directory
    """
    dir_path.mkdir(parents=True, exist_ok=True)
    set_directory_permissions(dir_path)


def validate_port(port: int) -> tuple[bool, str | None]:
    """Validate a port number.

    Args:
        port: Port number to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(port, int):
        return False, "Port must be an integer"

    if port < MIN_PORT or port > MAX_PORT:
        return False, f"Port must be between {MIN_PORT} and {MAX_PORT}"

    if port < SYSTEM_PORTS_WARNING:
        _LOGGER.warning(
            "Port %d is below %d and may require root privileges",
            port,
            SYSTEM_PORTS_WARNING,
        )

    return True, None


def validate_username(username: str) -> tuple[bool, str | None]:
    """Validate a username for basic auth.

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username cannot be empty"

    if len(username) < 1:
        return False, "Username must be at least 1 character"

    if len(username) > 32:
        return False, "Username must be 32 characters or less"

    # Only alphanumeric characters and underscore
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain alphanumeric characters and underscores"

    return True, None


def validate_password(password: str) -> tuple[bool, str | None]:
    """Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"

    # Check for at least one letter and one number
    has_letter = bool(re.search(r"[a-zA-Z]", password))
    has_number = bool(re.search(r"[0-9]", password))

    if not (has_letter and has_number):
        _LOGGER.warning("Password should contain both letters and numbers for better security")

    return True, None


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent directory traversal and other issues.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = os.path.basename(filename)
    # Remove any non-alphanumeric, dash, underscore, or dot characters
    filename = re.sub(r"[^a-zA-Z0-9._-]", "", filename)
    return filename


def check_port_available(port: int) -> bool:
    """Check if a port is available (basic check, not comprehensive).

    Note: This is a basic check. Full port conflict detection should be done
    by checking Docker containers.

    Args:
        port: Port number to check

    Returns:
        True if port appears available, False otherwise
    """
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            return result != 0  # Port is available if connection fails
    except Exception:
        # If we can't check, assume it might be available
        return True


def secure_file_write(file_path: Path, content: bytes | str, mode: int = PERM_CONFIG_FILE) -> None:
    """Write content to a file with secure permissions.

    Args:
        file_path: Path to the file
        content: Content to write (bytes or str)
        mode: Permission mode for the file
    """
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    if isinstance(content, str):
        file_path.write_text(content, encoding="utf-8")
    else:
        file_path.write_bytes(content)

    # Set secure permissions
    set_file_permissions(file_path, mode)

    _LOGGER.debug("Wrote secure file: %s", file_path)


def get_file_owner(file_path: Path) -> tuple[int, int] | None:
    """Get the owner UID and GID of a file.

    Args:
        file_path: Path to the file

    Returns:
        Tuple of (uid, gid) or None if unavailable
    """
    try:
        stat_info = os.stat(file_path)
        return (stat_info.st_uid, stat_info.st_gid)
    except OSError:
        return None


def is_file_secure(file_path: Path, expected_mode: int) -> bool:
    """Check if a file has the expected secure permissions.

    Args:
        file_path: Path to the file
        expected_mode: Expected permission mode

    Returns:
        True if file has expected permissions, False otherwise
    """
    try:
        current_mode = stat.S_IMODE(file_path.stat().st_mode)
        return current_mode == expected_mode
    except OSError:
        return False
