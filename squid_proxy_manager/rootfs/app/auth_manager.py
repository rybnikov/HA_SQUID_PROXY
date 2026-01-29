"""Basic auth user management (htpasswd generation)."""

import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

PERM_PASSWORD_FILE = 0o644


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

        self.passwd_file.write_text(content, encoding="utf-8")
        self.passwd_file.chmod(PERM_PASSWORD_FILE)
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
        if not username or len(username) < 1 or len(username) > 32:
            raise ValueError("Username must be 1-32 characters")
        if not username.replace("_", "").isalnum():
            raise ValueError("Username can only contain alphanumeric characters and underscores")

        # Validate password
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Load existing users
        self._load_users()

        # Check if user already exists
        if username in self._users:
            _LOGGER.warning("User %s already exists", username)
            return False

        # Generate MD5-crypt (apr1) hash compatible with Squid basic_ncsa_auth
        # We use openssl command as it's the most reliable way on Alpine
        try:
            import subprocess  # nosec B404

            result = subprocess.run(  # nosec B603,B607
                ["openssl", "passwd", "-apr1", password],
                capture_output=True,
                text=True,
                check=True,
            )
            password_hash = result.stdout.strip()
        except Exception as ex:
            _LOGGER.error("Failed to generate password hash using openssl: %s", ex)
            # Fallback to bcrypt if openssl fails (though it likely won't work with Squid)
            import bcrypt

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

    def get_users(self) -> list[str]:
        """Get list of usernames.

        Returns:
            List of usernames
        """
        self._load_users()
        return sorted(self._users.keys())

    def get_user_count(self) -> int:
        """Get the number of users.

        Returns:
            Number of users
        """
        self._load_users()
        return len(self._users)
