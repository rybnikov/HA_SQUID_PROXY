"""Integration tests for addon structure and Dockerfile validation."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
ADDON_DIR = PROJECT_ROOT / "squid_proxy_manager"
DOCKERFILE = ADDON_DIR / "Dockerfile"
ROOTFS_DIR = ADDON_DIR / "rootfs"
ROOTFS_APP_DIR = ROOTFS_DIR / "app"


class TestDockerfileStructure:
    """Test Dockerfile structure and syntax."""

    def test_dockerfile_exists(self):
        """Test that Dockerfile exists."""
        assert DOCKERFILE.exists(), f"Dockerfile not found at {DOCKERFILE}"

    def test_dockerfile_readable(self):
        """Test that Dockerfile can be read."""
        content = DOCKERFILE.read_text()
        assert len(content) > 0, "Dockerfile is empty"

    def test_dockerfile_has_build_from(self):
        """Test that Dockerfile has BUILD_FROM ARG with default."""
        content = DOCKERFILE.read_text()
        assert "ARG BUILD_FROM" in content, "Dockerfile missing BUILD_FROM ARG"
        assert (
            "ARG BUILD_FROM=" in content or "ARG BUILD_FROM = " in content
        ), "BUILD_FROM ARG should have a default value to avoid warnings"

    def test_dockerfile_has_from(self):
        """Test that Dockerfile has FROM instruction."""
        content = DOCKERFILE.read_text()
        assert "FROM" in content, "Dockerfile missing FROM instruction"

    def test_dockerfile_copies_rootfs(self):
        """Test that Dockerfile copies rootfs directory."""
        content = DOCKERFILE.read_text()
        assert (
            "COPY rootfs/" in content or "COPY rootfs /" in content
        ), "Dockerfile should copy rootfs directory"


class TestRequiredFiles:
    """Test that all required files exist."""

    def test_rootfs_app_main_py_exists(self):
        """Test that rootfs/app/main.py exists."""
        main_py = ROOTFS_APP_DIR / "main.py"
        assert (
            main_py.exists()
        ), "rootfs/app/main.py not found. This file is referenced in Dockerfile chmod command."

    def test_rootfs_app_proxy_manager_py_exists(self):
        """Test that rootfs/app/proxy_manager.py exists."""
        proxy_manager_py = ROOTFS_APP_DIR / "proxy_manager.py"
        assert (
            proxy_manager_py.exists()
        ), "rootfs/app/proxy_manager.py not found. This file is referenced in Dockerfile chmod command."

    def test_rootfs_app_squid_config_py_exists(self):
        """Test that rootfs/app/squid_config.py exists."""
        squid_config_py = ROOTFS_APP_DIR / "squid_config.py"
        assert (
            squid_config_py.exists()
        ), "rootfs/app/squid_config.py not found. This file is referenced in Dockerfile chmod command."

    def test_rootfs_app_cert_manager_py_exists(self):
        """Test that rootfs/app/cert_manager.py exists."""
        cert_manager_py = ROOTFS_APP_DIR / "cert_manager.py"
        assert (
            cert_manager_py.exists()
        ), "rootfs/app/cert_manager.py not found. This file is referenced in Dockerfile chmod command."

    def test_rootfs_app_auth_manager_py_exists(self):
        """Test that rootfs/app/auth_manager.py exists."""
        auth_manager_py = ROOTFS_APP_DIR / "auth_manager.py"
        assert (
            auth_manager_py.exists()
        ), "rootfs/app/auth_manager.py not found. This file is referenced in Dockerfile chmod command."


class TestDockerfileChmodCommands:
    """Test that Dockerfile chmod commands reference existing files."""

    def test_dockerfile_chmod_matches_files(self):
        """Test that all files in chmod commands exist."""
        dockerfile_content = DOCKERFILE.read_text()

        # Extract all chmod commands
        chmod_pattern = r"chmod\s+a\+x\s+([^\s\\]+)"
        chmod_files = re.findall(chmod_pattern, dockerfile_content)

        assert len(chmod_files) > 0, "No chmod commands found in Dockerfile"

        # Check each file exists in the expected location
        for file_path in chmod_files:
            # Remove leading slash for path resolution
            file_path_clean = file_path.lstrip("/")

            if file_path_clean.startswith("app/"):
                # Files in /app should be in rootfs/app/
                file_name = Path(file_path_clean).name
                expected_path = ROOTFS_APP_DIR / file_name
            elif file_path_clean.startswith("etc/"):
                # Files in /etc should be in rootfs/etc/
                expected_path = ROOTFS_DIR / file_path_clean
            else:
                # Assume it's in rootfs/app/
                expected_path = ROOTFS_APP_DIR / file_path_clean

            assert (
                expected_path.exists()
            ), f"File {file_path} referenced in Dockerfile chmod does not exist at {expected_path}"


class TestDockerfileSyntax:
    """Test Dockerfile syntax validation."""

    @pytest.mark.skipif(
        not shutil.which("docker"), reason="Docker not available, skipping syntax check"
    )
    def test_dockerfile_syntax_valid(self):
        """Test that Dockerfile has valid syntax using docker buildx."""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "buildx",
                    "build",
                    "--dry-run",
                    "--file",
                    str(DOCKERFILE),
                    str(ADDON_DIR),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0 and "unknown flag" in result.stderr.lower():
                result = subprocess.run(
                    [
                        "docker",
                        "buildx",
                        "build",
                        "--file",
                        str(DOCKERFILE),
                        "--target",
                        "nonexistent",
                        str(ADDON_DIR),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            if result.returncode != 0:
                error_output = result.stderr.lower()
                if any(
                    keyword in error_output
                    for keyword in [
                        "syntax",
                        "parse",
                        "invalid",
                        "unexpected",
                        "unknown instruction",
                        "bad flag",
                    ]
                ):
                    if "unknown target" not in error_output:
                        pytest.fail(f"Dockerfile syntax/parse error: {result.stderr}")
        except subprocess.TimeoutExpired:
            pytest.fail("Docker buildx command timed out")
        except FileNotFoundError:
            pytest.skip("docker command not found")


class TestDockerfileContent:
    """Test Dockerfile content and structure."""

    def test_dockerfile_installs_required_packages(self):
        """Test that Dockerfile installs required packages."""
        content = DOCKERFILE.read_text()

        required_packages = [
            "python3",
            "openssl",
            "bash",
            "curl",
            "squid",
            "cryptography",
            "bcrypt",
            "aiohttp",
        ]

        for package in required_packages:
            assert package in content.lower(), f"Dockerfile should install {package}"

    def test_dockerfile_sets_pythonpath(self):
        """Test that Dockerfile sets PYTHONPATH."""
        content = DOCKERFILE.read_text()
        assert "PYTHONPATH" in content, "Dockerfile should set PYTHONPATH environment variable"

    def test_dockerfile_has_workdir(self):
        """Test that Dockerfile sets WORKDIR."""
        content = DOCKERFILE.read_text()
        assert "WORKDIR" in content, "Dockerfile should set WORKDIR"

    def test_dockerfile_has_labels(self):
        """Test that Dockerfile has Home Assistant labels."""
        content = DOCKERFILE.read_text()
        assert "io.hass.name" in content, "Dockerfile should have io.hass.name label"
        assert "io.hass.type" in content, "Dockerfile should have io.hass.type label"
