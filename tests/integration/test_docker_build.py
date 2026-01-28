"""Integration tests for Docker build validation."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
ADDON_DIR = PROJECT_ROOT / "squid_proxy_manager"
DOCKERFILE = ADDON_DIR / "Dockerfile"
DOCKERFILE_SQUID = ADDON_DIR / "Dockerfile.squid"
ROOTFS_DIR = ADDON_DIR / "rootfs"
ROOTFS_APP_DIR = ROOTFS_DIR / "app"


class TestDockerfileStructure:
    """Test Dockerfile structure and syntax."""

    def test_dockerfile_exists(self):
        """Test that Dockerfile exists."""
        assert DOCKERFILE.exists(), f"Dockerfile not found at {DOCKERFILE}"

    def test_dockerfile_squid_exists(self):
        """Test that Dockerfile.squid exists."""
        assert DOCKERFILE_SQUID.exists(), f"Dockerfile.squid not found at {DOCKERFILE_SQUID}"

    def test_dockerfile_readable(self):
        """Test that Dockerfile can be read."""
        content = DOCKERFILE.read_text()
        assert len(content) > 0, "Dockerfile is empty"

    def test_dockerfile_has_build_from(self):
        """Test that Dockerfile has BUILD_FROM ARG with default."""
        content = DOCKERFILE.read_text()
        # Check for ARG BUILD_FROM with default value
        assert "ARG BUILD_FROM" in content, "Dockerfile missing BUILD_FROM ARG"
        # Check that it has a default value to avoid warnings
        assert "ARG BUILD_FROM=" in content or "ARG BUILD_FROM = " in content, \
            "BUILD_FROM ARG should have a default value to avoid warnings"

    def test_dockerfile_has_from(self):
        """Test that Dockerfile has FROM instruction."""
        content = DOCKERFILE.read_text()
        assert "FROM" in content, "Dockerfile missing FROM instruction"

    def test_dockerfile_copies_rootfs(self):
        """Test that Dockerfile copies rootfs directory."""
        content = DOCKERFILE.read_text()
        assert "COPY rootfs/" in content or "COPY rootfs /" in content, \
            "Dockerfile should copy rootfs directory"

    def test_dockerfile_copies_dockerfile_squid(self):
        """Test that Dockerfile copies Dockerfile.squid."""
        content = DOCKERFILE.read_text()
        assert "Dockerfile.squid" in content, \
            "Dockerfile should copy Dockerfile.squid"


class TestRequiredFiles:
    """Test that all required files exist."""

    def test_rootfs_run_sh_exists(self):
        """Test that rootfs/run.sh exists (required for chmod in Dockerfile)."""
        run_sh = ROOTFS_DIR / "run.sh"
        assert run_sh.exists(), \
            f"rootfs/run.sh not found. This file is required and referenced in Dockerfile chmod command."

    def test_rootfs_app_main_py_exists(self):
        """Test that rootfs/app/main.py exists."""
        main_py = ROOTFS_APP_DIR / "main.py"
        assert main_py.exists(), \
            f"rootfs/app/main.py not found. This file is referenced in Dockerfile chmod command."

    def test_rootfs_app_proxy_manager_py_exists(self):
        """Test that rootfs/app/proxy_manager.py exists."""
        proxy_manager_py = ROOTFS_APP_DIR / "proxy_manager.py"
        assert proxy_manager_py.exists(), \
            f"rootfs/app/proxy_manager.py not found. This file is referenced in Dockerfile chmod command."

    def test_rootfs_app_squid_config_py_exists(self):
        """Test that rootfs/app/squid_config.py exists."""
        squid_config_py = ROOTFS_APP_DIR / "squid_config.py"
        assert squid_config_py.exists(), \
            f"rootfs/app/squid_config.py not found. This file is referenced in Dockerfile chmod command."

    def test_rootfs_app_cert_manager_py_exists(self):
        """Test that rootfs/app/cert_manager.py exists."""
        cert_manager_py = ROOTFS_APP_DIR / "cert_manager.py"
        assert cert_manager_py.exists(), \
            f"rootfs/app/cert_manager.py not found. This file is referenced in Dockerfile chmod command."

    def test_rootfs_app_auth_manager_py_exists(self):
        """Test that rootfs/app/auth_manager.py exists."""
        auth_manager_py = ROOTFS_APP_DIR / "auth_manager.py"
        assert auth_manager_py.exists(), \
            f"rootfs/app/auth_manager.py not found. This file is referenced in Dockerfile chmod command."

    def test_rootfs_app_build_squid_image_sh_exists(self):
        """Test that rootfs/app/build_squid_image.sh exists."""
        build_squid_image_sh = ROOTFS_APP_DIR / "build_squid_image.sh"
        assert build_squid_image_sh.exists(), \
            f"rootfs/app/build_squid_image.sh not found. This file is referenced in Dockerfile chmod command."


class TestDockerfileChmodCommands:
    """Test that Dockerfile chmod commands reference existing files."""

    def test_dockerfile_chmod_matches_files(self):
        """Test that all files in chmod commands exist."""
        dockerfile_content = DOCKERFILE.read_text()
        
        # Extract all chmod commands
        chmod_pattern = r'chmod\s+a\+x\s+([^\s\\]+)'
        chmod_files = re.findall(chmod_pattern, dockerfile_content)
        
        assert len(chmod_files) > 0, "No chmod commands found in Dockerfile"
        
        # Check each file exists in the expected location
        for file_path in chmod_files:
            # Remove leading slash for path resolution
            file_path_clean = file_path.lstrip('/')
            
            if file_path_clean == "run.sh":
                # run.sh should be in rootfs/
                expected_path = ROOTFS_DIR / "run.sh"
            elif file_path_clean.startswith("app/"):
                # Files in /app should be in rootfs/app/
                file_name = Path(file_path_clean).name
                expected_path = ROOTFS_APP_DIR / file_name
            elif file_path_clean.startswith("etc/"):
                # Files in /etc should be in rootfs/etc/
                expected_path = ROOTFS_DIR / file_path_clean
            else:
                # Assume it's in rootfs/app/
                expected_path = ROOTFS_APP_DIR / file_path_clean
            
            assert expected_path.exists(), \
                f"File {file_path} referenced in Dockerfile chmod does not exist at {expected_path}"


class TestDockerfileSyntax:
    """Test Dockerfile syntax validation."""

    @pytest.mark.skipif(
        not shutil.which("docker"),
        reason="Docker not available, skipping syntax check"
    )
    def test_dockerfile_syntax_valid(self):
        """Test that Dockerfile has valid syntax using docker buildx."""
        # This test requires docker to be available
        # We'll try to parse the Dockerfile using docker buildx
        try:
            # Try with --dry-run first (if supported)
            result = subprocess.run(
                [
                    "docker", "buildx", "build",
                    "--dry-run",
                    "--file", str(DOCKERFILE),
                    str(ADDON_DIR)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # If dry-run is not supported, try a regular build with --no-cache
            # but stop early by checking just the parsing phase
            if result.returncode != 0 and "unknown flag" in result.stderr.lower():
                # Fallback: try to build with --target to stop early
                # or just check that docker can parse the file
                result = subprocess.run(
                    [
                        "docker", "buildx", "build",
                        "--file", str(DOCKERFILE),
                        "--target", "nonexistent",  # This will fail early but parse the file
                        str(ADDON_DIR)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            # Check if it's a syntax/parse error
            if result.returncode != 0:
                error_output = result.stderr.lower()
                # Syntax errors are critical
                if any(keyword in error_output for keyword in [
                    "syntax", "parse", "invalid", "unexpected", 
                    "unknown instruction", "bad flag"
                ]):
                    # But ignore "unknown target" as that's expected in our fallback
                    if "unknown target" not in error_output:
                        pytest.fail(f"Dockerfile syntax/parse error: {result.stderr}")
        except subprocess.TimeoutExpired:
            pytest.fail("Docker buildx command timed out")
        except FileNotFoundError:
            pytest.skip("docker command not found")

    def test_dockerfile_no_invalid_chmod_paths(self):
        """Test that Dockerfile doesn't reference non-existent files in chmod."""
        dockerfile_content = DOCKERFILE.read_text()
        
        # Extract chmod commands
        chmod_pattern = r'chmod\s+a\+x\s+([^\s\\]+)'
        chmod_files = re.findall(chmod_pattern, dockerfile_content)
        
        missing_files = []
        for file_path in chmod_files:
            file_path_clean = file_path.lstrip('/')
            
            if file_path_clean == "run.sh":
                expected_path = ROOTFS_DIR / "run.sh"
            elif file_path_clean.startswith("app/"):
                file_name = Path(file_path_clean).name
                expected_path = ROOTFS_APP_DIR / file_name
            elif file_path_clean.startswith("etc/"):
                # Files in /etc should be in rootfs/etc/
                expected_path = ROOTFS_DIR / file_path_clean
            else:
                expected_path = ROOTFS_APP_DIR / file_path_clean
            
            if not expected_path.exists():
                missing_files.append((file_path, expected_path))
        
        assert len(missing_files) == 0, \
            f"Files referenced in Dockerfile chmod do not exist: {missing_files}"


class TestDockerfileContent:
    """Test Dockerfile content and structure."""

    def test_dockerfile_installs_required_packages(self):
        """Test that Dockerfile installs required Python packages."""
        content = DOCKERFILE.read_text()
        
        required_packages = [
            "python3",
            "docker",
            "cryptography",
            "bcrypt",
            "aiohttp"
        ]
        
        for package in required_packages:
            assert package in content.lower(), \
                f"Dockerfile should install {package}"

    def test_dockerfile_sets_pythonpath(self):
        """Test that Dockerfile sets PYTHONPATH."""
        content = DOCKERFILE.read_text()
        assert "PYTHONPATH" in content, \
            "Dockerfile should set PYTHONPATH environment variable"

    def test_dockerfile_has_workdir(self):
        """Test that Dockerfile sets WORKDIR."""
        content = DOCKERFILE.read_text()
        assert "WORKDIR" in content, \
            "Dockerfile should set WORKDIR"

    def test_dockerfile_has_labels(self):
        """Test that Dockerfile has Home Assistant labels."""
        content = DOCKERFILE.read_text()
        assert "io.hass.name" in content, \
            "Dockerfile should have io.hass.name label"
        assert "io.hass.type" in content, \
            "Dockerfile should have io.hass.type label"
