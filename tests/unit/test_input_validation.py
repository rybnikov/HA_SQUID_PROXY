"""Tests for input validation helpers."""

import pytest
from auth_manager import AuthManager
from proxy_manager import validate_instance_name, validate_port


def test_validate_instance_name_rejects_traversal():
    with pytest.raises(ValueError):
        validate_instance_name("../etc/passwd")


def test_validate_instance_name_rejects_invalid_chars():
    with pytest.raises(ValueError):
        validate_instance_name("bad$name")


def test_validate_instance_name_accepts_valid():
    validate_instance_name("proxy_1-foo")


def test_validate_port_out_of_range():
    with pytest.raises(ValueError):
        validate_port(80)


@pytest.mark.parametrize("port", [1024, 3128, 65535])
def test_validate_port_ok(port):
    validate_port(port)


def test_validate_username_pattern(tmp_path):
    passwd_file = tmp_path / "passwd"
    auth = AuthManager(passwd_file)
    with pytest.raises(ValueError):
        auth.add_user("bad$user", "password123")
