"""Unit tests for TLS tunnel support in ProxyInstanceManager."""

import json
import signal
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "squid_proxy_manager" / "rootfs" / "app")
)


@pytest.fixture
def mock_popen():
    """Mock subprocess.Popen for process management tests."""
    with patch("subprocess.Popen") as mock_popen_class:
        mock_process = MagicMock()
        mock_process.pid = 54321
        mock_process.poll.return_value = None  # Running
        mock_popen_class.return_value = mock_process
        yield mock_popen_class


@pytest.fixture
def temp_data_dir(temp_dir):
    """Create temporary data directory structure."""
    data_dir = temp_dir / "data"
    (data_dir / "squid_proxy_manager").mkdir(parents=True)
    (data_dir / "squid_proxy_manager" / "certs").mkdir(parents=True)
    (data_dir / "squid_proxy_manager" / "logs").mkdir(parents=True)
    return data_dir


@pytest.fixture
def patched_dirs(temp_data_dir):
    """Context manager-like fixture that patches all directory and binary constants."""
    return {
        "proxy_manager.DATA_DIR": temp_data_dir,
        "proxy_manager.CONFIG_DIR": temp_data_dir / "squid_proxy_manager",
        "proxy_manager.CERTS_DIR": temp_data_dir / "squid_proxy_manager" / "certs",
        "proxy_manager.LOGS_DIR": temp_data_dir / "squid_proxy_manager" / "logs",
        "proxy_manager.NGINX_BINARY": "/usr/sbin/nginx",
    }


# ---------------------------------------------------------------------------
# create_instance with proxy_type="tls_tunnel"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tls_tunnel_instance(mock_popen, temp_data_dir):
    """POST create_instance with proxy_type='tls_tunnel' should generate nginx configs and store metadata."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
        patch("proxy_manager.NGINX_BINARY", "/usr/sbin/nginx"),
        patch("os.path.exists", return_value=True),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        instance = await manager.create_instance(
            name="vpn-tunnel",
            port=8443,
            proxy_type="tls_tunnel",
            forward_address="vpn.example.com:1194",
            cover_domain="mysite.example.com",
        )

        assert instance["name"] == "vpn-tunnel"
        assert instance["proxy_type"] == "tls_tunnel"
        assert instance["port"] == 8443
        assert instance["forward_address"] == "vpn.example.com:1194"
        assert instance["cover_domain"] == "mysite.example.com"
        assert instance["status"] == "running"

        # Verify instance.json metadata
        instance_dir = temp_data_dir / "squid_proxy_manager" / "vpn-tunnel"
        metadata_file = instance_dir / "instance.json"
        assert metadata_file.exists()
        metadata = json.loads(metadata_file.read_text())
        assert metadata["proxy_type"] == "tls_tunnel"
        assert metadata["forward_address"] == "vpn.example.com:1194"
        assert metadata["cover_domain"] == "mysite.example.com"
        assert metadata["port"] == 8443
        assert "cover_site_port" in metadata

        # Verify nginx config files were generated
        assert (instance_dir / "nginx_stream.conf").exists()
        assert (instance_dir / "nginx_cover.conf").exists()

        # Verify cover site certificate was generated
        assert (instance_dir / "certs" / "cover.crt").exists()
        assert (instance_dir / "certs" / "cover.key").exists()

        # Verify process was started
        assert "vpn-tunnel" in manager.processes
        mock_popen.assert_called_once()


@pytest.mark.asyncio
async def test_create_tls_tunnel_missing_forward_address(temp_data_dir):
    """create_instance with proxy_type='tls_tunnel' but no forward_address should raise ValueError."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
        patch("proxy_manager.NGINX_BINARY", "/usr/sbin/nginx"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        with pytest.raises(ValueError, match="forward_address is required"):
            await manager.create_instance(
                name="tunnel-no-fwd",
                port=8443,
                proxy_type="tls_tunnel",
            )


@pytest.mark.asyncio
async def test_create_tls_tunnel_invalid_forward_address(temp_data_dir):
    """create_instance with invalid forward_address format should raise ValueError."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
        patch("proxy_manager.NGINX_BINARY", "/usr/sbin/nginx"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        with pytest.raises(ValueError, match="Invalid forward address"):
            await manager.create_instance(
                name="tunnel-bad-fwd",
                port=8443,
                proxy_type="tls_tunnel",
                forward_address="not_valid",
            )


@pytest.mark.asyncio
async def test_create_tls_tunnel_invalid_proxy_type(temp_data_dir):
    """create_instance with invalid proxy_type should raise ValueError."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        with pytest.raises(ValueError, match="Invalid proxy_type"):
            await manager.create_instance(
                name="bad-type",
                port=8443,
                proxy_type="wireguard",
            )


@pytest.mark.asyncio
async def test_create_tls_tunnel_cover_domain_defaults_empty(mock_popen, temp_data_dir):
    """cover_domain should default to empty string when not provided."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
        patch("proxy_manager.NGINX_BINARY", "/usr/sbin/nginx"),
        patch("os.path.exists", return_value=True),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        instance = await manager.create_instance(
            name="tunnel-no-cover",
            port=8443,
            proxy_type="tls_tunnel",
            forward_address="vpn:1194",
        )

        assert instance["cover_domain"] == ""


# ---------------------------------------------------------------------------
# get_instances with tls_tunnel instances
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_instances_detects_tls_tunnel(temp_data_dir):
    """get_instances should detect tls_tunnel instances via instance.json."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Set up a TLS tunnel instance directory
        instance_dir = temp_data_dir / "squid_proxy_manager" / "vpn-tunnel"
        instance_dir.mkdir(parents=True)
        metadata = {
            "name": "vpn-tunnel",
            "proxy_type": "tls_tunnel",
            "port": 8443,
            "forward_address": "vpn.example.com:1194",
            "cover_domain": "mysite.example.com",
            "cover_site_port": 18443,
        }
        (instance_dir / "instance.json").write_text(json.dumps(metadata))
        (instance_dir / "nginx_stream.conf").touch()

        instances = await manager.get_instances()

        assert len(instances) == 1
        inst = instances[0]
        assert inst["name"] == "vpn-tunnel"
        assert inst["proxy_type"] == "tls_tunnel"
        assert inst["port"] == 8443
        assert inst["forward_address"] == "vpn.example.com:1194"
        assert inst["cover_domain"] == "mysite.example.com"
        assert inst["https_enabled"] is False  # always False for tls_tunnel
        assert inst["dpi_prevention"] is False  # always False for tls_tunnel
        # tls_tunnel should NOT have user_count
        assert "user_count" not in inst


# ---------------------------------------------------------------------------
# start_instance for tls_tunnel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_tls_tunnel_instance_calls_nginx(mock_popen, temp_data_dir):
    """start_instance for tls_tunnel should invoke the nginx binary."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
        patch("proxy_manager.NGINX_BINARY", "/usr/sbin/nginx"),
        patch("os.path.exists", return_value=True),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Create instance directory with required files
        instance_dir = temp_data_dir / "squid_proxy_manager" / "tls-inst"
        instance_dir.mkdir(parents=True)
        (instance_dir / "nginx_stream.conf").write_text("stream {}")
        metadata = {"proxy_type": "tls_tunnel", "port": 8443}
        (instance_dir / "instance.json").write_text(json.dumps(metadata))

        result = await manager.start_instance("tls-inst")

        assert result is True
        assert "tls-inst" in manager.processes
        mock_popen.assert_called_once()
        # Verify nginx was called with -c and the stream config
        call_args = mock_popen.call_args[0][0]  # First positional arg (cmd list)
        assert call_args[0] == "/usr/sbin/nginx"
        assert "-c" in call_args
        assert "nginx_stream.conf" in call_args[call_args.index("-c") + 1]


@pytest.mark.asyncio
async def test_start_tls_tunnel_missing_config(temp_data_dir):
    """start_instance for tls_tunnel should return False if nginx_stream.conf is missing."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
        patch("proxy_manager.NGINX_BINARY", "/usr/sbin/nginx"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Create instance directory with metadata but NO nginx_stream.conf
        instance_dir = temp_data_dir / "squid_proxy_manager" / "tls-missing"
        instance_dir.mkdir(parents=True)
        metadata = {"proxy_type": "tls_tunnel"}
        (instance_dir / "instance.json").write_text(json.dumps(metadata))

        result = await manager.start_instance("tls-missing")

        assert result is False


# ---------------------------------------------------------------------------
# stop_instance for tls_tunnel (SIGQUIT)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_tls_tunnel_sends_sigquit(temp_data_dir):
    """stop_instance for tls_tunnel should send SIGQUIT (graceful nginx shutdown), not SIGTERM."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
        patch("os.killpg") as mock_killpg,
        patch("os.getpgid", return_value=999),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Set up instance as tls_tunnel type
        instance_dir = temp_data_dir / "squid_proxy_manager" / "tls-stop"
        instance_dir.mkdir(parents=True)
        metadata = {"proxy_type": "tls_tunnel"}
        (instance_dir / "instance.json").write_text(json.dumps(metadata))

        mock_process = MagicMock()
        mock_process.pid = 54321
        # First poll returns None (running), then 0 (stopped) for remaining calls
        mock_process.poll.side_effect = [None, None, 0, 0, 0, 0]
        manager.processes["tls-stop"] = mock_process

        result = await manager.stop_instance("tls-stop")

        assert result is True
        assert "tls-stop" not in manager.processes

        # Verify SIGQUIT was sent (not SIGTERM)
        mock_killpg.assert_any_call(999, signal.SIGQUIT)


# ---------------------------------------------------------------------------
# update_instance for tls_tunnel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_tls_tunnel_forward_address(temp_data_dir):
    """update_instance for tls_tunnel should update forward_address and regenerate config."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Set up existing tls_tunnel instance
        instance_dir = temp_data_dir / "squid_proxy_manager" / "update-tunnel"
        instance_dir.mkdir(parents=True)
        (instance_dir / "certs").mkdir()
        (instance_dir / "certs" / "cover.crt").touch()
        (instance_dir / "certs" / "cover.key").touch()
        metadata = {
            "name": "update-tunnel",
            "proxy_type": "tls_tunnel",
            "port": 8443,
            "forward_address": "old-vpn:1194",
            "cover_domain": "old.example.com",
            "cover_site_port": 18443,
        }
        (instance_dir / "instance.json").write_text(json.dumps(metadata))
        (instance_dir / "nginx_stream.conf").write_text("old config")

        result = await manager.update_instance(
            "update-tunnel",
            forward_address="new-vpn:1195",
            cover_domain="new.example.com",
        )

        assert result is True

        # Verify metadata updated
        updated_metadata = json.loads((instance_dir / "instance.json").read_text())
        assert updated_metadata["forward_address"] == "new-vpn:1195"
        assert updated_metadata["cover_domain"] == "new.example.com"

        # Verify config was regenerated
        stream_content = (instance_dir / "nginx_stream.conf").read_text()
        assert "new-vpn:1195" in stream_content
        assert "old-vpn" not in stream_content


@pytest.mark.asyncio
async def test_update_tls_tunnel_port(temp_data_dir):
    """update_instance for tls_tunnel should update the listening port."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        instance_dir = temp_data_dir / "squid_proxy_manager" / "port-tunnel"
        instance_dir.mkdir(parents=True)
        (instance_dir / "certs").mkdir()
        (instance_dir / "certs" / "cover.crt").touch()
        (instance_dir / "certs" / "cover.key").touch()
        metadata = {
            "name": "port-tunnel",
            "proxy_type": "tls_tunnel",
            "port": 8443,
            "forward_address": "vpn:1194",
            "cover_domain": "",
            "cover_site_port": 18443,
        }
        (instance_dir / "instance.json").write_text(json.dumps(metadata))
        (instance_dir / "nginx_stream.conf").write_text("placeholder")

        result = await manager.update_instance("port-tunnel", port=9443)

        assert result is True
        updated_metadata = json.loads((instance_dir / "instance.json").read_text())
        assert updated_metadata["port"] == 9443

        stream_content = (instance_dir / "nginx_stream.conf").read_text()
        assert "listen 9443" in stream_content


# ---------------------------------------------------------------------------
# Backward compatibility - missing proxy_type defaults to squid
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_proxy_type_defaults_to_squid(temp_data_dir):
    """_get_proxy_type should return 'squid' when instance.json has no proxy_type field."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Instance with instance.json that has no proxy_type
        instance_dir = temp_data_dir / "squid_proxy_manager" / "legacy-inst"
        instance_dir.mkdir(parents=True)
        metadata = {"name": "legacy-inst", "port": 3128}
        (instance_dir / "instance.json").write_text(json.dumps(metadata))

        assert manager._get_proxy_type("legacy-inst") == "squid"


@pytest.mark.asyncio
async def test_get_proxy_type_defaults_when_no_metadata(temp_data_dir):
    """_get_proxy_type should return 'squid' when instance.json does not exist."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Instance directory exists but no instance.json
        instance_dir = temp_data_dir / "squid_proxy_manager" / "no-meta"
        instance_dir.mkdir(parents=True)

        assert manager._get_proxy_type("no-meta") == "squid"


@pytest.mark.asyncio
async def test_get_instances_legacy_squid_no_metadata(temp_data_dir):
    """get_instances should detect legacy squid instances (squid.conf but no instance.json)."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Legacy instance with squid.conf only
        instance_dir = temp_data_dir / "squid_proxy_manager" / "legacy"
        instance_dir.mkdir(parents=True)
        (instance_dir / "squid.conf").write_text("http_port 3128\n")

        instances = await manager.get_instances()

        assert len(instances) == 1
        inst = instances[0]
        assert inst["proxy_type"] == "squid"
        assert inst["port"] == 3128


# ---------------------------------------------------------------------------
# Cover site port allocation logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cover_site_port_allocation(mock_popen, temp_data_dir):
    """cover_site_port should be port + 10000, with fallback if > 65535."""
    with (
        patch("proxy_manager.DATA_DIR", temp_data_dir),
        patch("proxy_manager.CONFIG_DIR", temp_data_dir / "squid_proxy_manager"),
        patch("proxy_manager.CERTS_DIR", temp_data_dir / "squid_proxy_manager" / "certs"),
        patch("proxy_manager.LOGS_DIR", temp_data_dir / "squid_proxy_manager" / "logs"),
        patch("proxy_manager.NGINX_BINARY", "/usr/sbin/nginx"),
        patch("os.path.exists", return_value=True),
    ):
        from proxy_manager import ProxyInstanceManager

        manager = ProxyInstanceManager()

        # Normal case: port=8443 -> cover_site_port=18443
        await manager.create_instance(
            name="port-test",
            port=8443,
            proxy_type="tls_tunnel",
            forward_address="vpn:1194",
        )

        instance_dir = temp_data_dir / "squid_proxy_manager" / "port-test"
        metadata = json.loads((instance_dir / "instance.json").read_text())
        assert metadata["cover_site_port"] == 18443
