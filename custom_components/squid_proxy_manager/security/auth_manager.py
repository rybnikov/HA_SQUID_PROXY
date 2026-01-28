"""Basic auth user management (htpasswd generation)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import bcrypt

from ..const import PERM_PASSWORD_FILE
from .security_utils import secure_file_write, validate_password, validate_username

_LOGGER = logging.getLogger(__name__)


class AuthManager:
    """Manages basic authentication users for proxy instances."""

    def __init__(self, passwd_file: Path) -> None:
        """Initialize auth manager.

        Args:
            passwd_file: Path to htpasswd file
        """
        self.passwd_file = passwd_file
        self._users: dict[str, str] = {}  # username -> bcrypt hash

    def _load_users(self) -> None:
        """Load users from htpasswd file."""
        self._users = {}
        if not self.passwd_file.exists():
            return

        try:
            content = self.passwd_file.read_text(encoding="utf-8")
            for line in content.strip().split("\n"):
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":", 1)
                if len(parts) == 2:
                    username, password_hash = parts
                    self._users[username] = password_hash
            _LOGGER.debug("Loaded %d users from %s", len(self._users), self.passwd_file)
        except Exception as ex:
            _LOGGER.error("Failed to load users from %s: %s", self.passwd_file, ex)
            raise

    def _save_users(self) -> None:
        """Save users to htpasswd file."""
        lines = []
        for username, password_hash in sorted(self._users.items()):
            lines.append(f"{username}:{password_hash}")

        content = "\n".join(lines)
        if lines:
            content += "\n"

        secure_file_write(self.passwd_file, content, PERM_PASSWORD_FILE)
        _LOGGER.debug("Saved %d users to %s", len(self._users), self.passwd_file)

    def add_user(self, username: str, password: str) -> bool:
        """Add a new user.

        Args:
            username: Username
            password: Plain text password

        Returns:
            True if user was added, False if user already exists

        Raises:
            ValueError: If username or password is invalid
        """
        # Validate username
        is_valid, error = validate_username(username)
        if not is_valid:
            raise ValueError(error)

        # Validate password
        is_valid, error = validate_password(password)
        if not is_valid:
            raise ValueError(error)

        # Load existing users
        self._load_users()

        # Check if user already exists
        if username in self._users:
            _LOGGER.warning("User %s already exists", username)
            return False

        # Hash password with bcrypt
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

        # Add user
        self._users[username] = password_hash
        self._save_users()

        _LOGGER.info("Added user: %s", username)
        return True

    def remove_user(self, username: str) -> bool:
        """Remove a user.

        Args:
            username: Username to remove

        Returns:
            True if user was removed, False if user doesn't exist
        """
        # Load existing users
        self._load_users()

        if username not in self._users:
            _LOGGER.warning("User %s does not exist", username)
            return False

        # Remove user
        del self._users[username]
        self._save_users()

        _LOGGER.info("Removed user: %s", username)
        return True

    def update_user_password(self, username: str, password: str) -> bool:
        """Update a user's password.

        Args:
            username: Username
            password: New plain text password

        Returns:
            True if password was updated, False if user doesn't exist

        Raises:
            ValueError: If password is invalid
        """
        # Validate password
        is_valid, error = validate_password(password)
        if not is_valid:
            raise ValueError(error)

        # Load existing users
        self._load_users()

        if username not in self._users:
            _LOGGER.warning("User %s does not exist", username)
            return False

        # Hash new password
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

        # Update user
        self._users[username] = password_hash
        self._save_users()

        _LOGGER.info("Updated password for user: %s", username)
        return True

    def get_users(self) -> list[str]:
        """Get list of usernames.

        Returns:
            List of usernames
        """
        self._load_users()
        return sorted(self._users.keys())

    def user_exists(self, username: str) -> bool:
        """Check if a user exists.

        Args:
            username: Username to check

        Returns:
            True if user exists, False otherwise
        """
        self._load_users()
        return username in self._users

    def get_user_count(self) -> int:
        """Get the number of users.

        Returns:
            Number of users
        """
        self._load_users()
        return len(self._users)
