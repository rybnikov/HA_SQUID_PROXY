"""Tests for AuthManager."""
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app"))

from auth_manager import AuthManager


def test_auth_manager_init(temp_dir):
    """Test AuthManager initialization."""
    passwd_file = temp_dir / "passwd"
    auth_manager = AuthManager(passwd_file)
    assert auth_manager.passwd_file == passwd_file


def test_add_user(temp_dir):
    """Test adding a user."""
    passwd_file = temp_dir / "passwd"
    auth_manager = AuthManager(passwd_file)
    
    result = auth_manager.add_user("testuser", "password123")
    assert result is True
    assert passwd_file.exists()
    
    # Check permissions
    assert oct(passwd_file.stat().st_mode)[-3:] == "600"
    
    # Check user was added
    users = auth_manager.get_users()
    assert "testuser" in users


def test_add_user_duplicate(temp_dir):
    """Test adding a duplicate user."""
    passwd_file = temp_dir / "passwd"
    auth_manager = AuthManager(passwd_file)
    
    auth_manager.add_user("testuser", "password123")
    result = auth_manager.add_user("testuser", "password456")
    
    assert result is False  # User already exists


def test_add_user_invalid_username(temp_dir):
    """Test adding user with invalid username."""
    passwd_file = temp_dir / "passwd"
    auth_manager = AuthManager(passwd_file)
    
    with pytest.raises(ValueError, match="Username must be 1-32 characters"):
        auth_manager.add_user("", "password123")
    
    with pytest.raises(ValueError, match="Username can only contain"):
        auth_manager.add_user("user@name", "password123")


def test_add_user_invalid_password(temp_dir):
    """Test adding user with invalid password."""
    passwd_file = temp_dir / "passwd"
    auth_manager = AuthManager(passwd_file)
    
    with pytest.raises(ValueError, match="Password must be at least 8 characters"):
        auth_manager.add_user("testuser", "short")


def test_remove_user(temp_dir):
    """Test removing a user."""
    passwd_file = temp_dir / "passwd"
    auth_manager = AuthManager(passwd_file)
    
    auth_manager.add_user("testuser", "password123")
    assert "testuser" in auth_manager.get_users()
    
    result = auth_manager.remove_user("testuser")
    assert result is True
    assert "testuser" not in auth_manager.get_users()


def test_remove_nonexistent_user(temp_dir):
    """Test removing a user that doesn't exist."""
    passwd_file = temp_dir / "passwd"
    auth_manager = AuthManager(passwd_file)
    
    result = auth_manager.remove_user("nonexistent")
    assert result is False


def test_get_users(temp_dir):
    """Test getting list of users."""
    passwd_file = temp_dir / "passwd"
    auth_manager = AuthManager(passwd_file)
    
    assert auth_manager.get_users() == []
    
    auth_manager.add_user("user1", "password123")
    auth_manager.add_user("user2", "password456")
    
    users = auth_manager.get_users()
    assert len(users) == 2
    assert "user1" in users
    assert "user2" in users


def test_get_user_count(temp_dir):
    """Test getting user count."""
    passwd_file = temp_dir / "passwd"
    auth_manager = AuthManager(passwd_file)
    
    assert auth_manager.get_user_count() == 0
    
    auth_manager.add_user("user1", "password123")
    assert auth_manager.get_user_count() == 1
    
    auth_manager.add_user("user2", "password456")
    assert auth_manager.get_user_count() == 2
    
    auth_manager.remove_user("user1")
    assert auth_manager.get_user_count() == 1


def test_load_existing_users(temp_dir):
    """Test loading existing users from file."""
    passwd_file = temp_dir / "passwd"
    
    # Create file with existing users
    import bcrypt
    password_hash = bcrypt.hashpw("password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    passwd_file.write_text(f"user1:{password_hash}\n")
    passwd_file.chmod(0o600)
    
    auth_manager = AuthManager(passwd_file)
    users = auth_manager.get_users()
    assert "user1" in users
