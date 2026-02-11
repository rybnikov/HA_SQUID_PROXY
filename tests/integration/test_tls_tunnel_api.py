"""Integration tests for TLS tunnel API endpoints (Process-based)."""

import sys
from pathlib import Path

import pytest

# Add integration tests directory to path for test_helpers
sys.path.insert(0, str(Path(__file__).parent))
from test_helpers import call_handler

# ---------------------------------------------------------------------------
# POST /api/instances — create tls_tunnel instance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tls_tunnel_instance_e2e(app_with_manager, test_port):
    """Create a tls_tunnel instance via the API and verify the response."""
    resp = await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "tls-api-test",
            "port": test_port,
            "proxy_type": "tls_tunnel",
            "forward_address": "vpn.example.com:1194",
            "cover_domain": "mysite.example.com",
        },
    )
    assert resp.status == 201
    data = await resp.json()
    assert data["status"] == "created"
    assert data["instance"]["proxy_type"] == "tls_tunnel"
    assert data["instance"]["forward_address"] == "vpn.example.com:1194"
    assert data["instance"]["cover_domain"] == "mysite.example.com"
    assert data["instance"]["port"] == test_port


@pytest.mark.asyncio
async def test_create_tls_tunnel_missing_forward_address_e2e(app_with_manager, test_port):
    """Creating a tls_tunnel instance without forward_address should return 400."""
    resp = await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "tls-no-fwd",
            "port": test_port,
            "proxy_type": "tls_tunnel",
        },
    )
    assert resp.status == 400
    data = await resp.json()
    assert "error" in data
    assert "forward_address" in data["error"]


@pytest.mark.asyncio
async def test_create_tls_tunnel_invalid_forward_address_e2e(app_with_manager, test_port):
    """Creating a tls_tunnel instance with invalid forward_address should return 400."""
    resp = await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "tls-bad-fwd",
            "port": test_port,
            "proxy_type": "tls_tunnel",
            "forward_address": "not_valid",
        },
    )
    assert resp.status == 400
    data = await resp.json()
    assert "error" in data


# ---------------------------------------------------------------------------
# GET /api/instances — verify tls_tunnel instance in listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_instances_includes_tls_tunnel_e2e(app_with_manager, test_port):
    """GET /api/instances should list the tls_tunnel instance with correct fields."""
    # Create tls_tunnel instance first
    await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "tls-list-test",
            "port": test_port,
            "proxy_type": "tls_tunnel",
            "forward_address": "vpn.test.com:1194",
            "cover_domain": "cover.test.com",
        },
    )

    resp = await call_handler(app_with_manager, "GET", "/api/instances")
    assert resp.status == 200
    data = await resp.json()

    tls_instance = next((i for i in data["instances"] if i["name"] == "tls-list-test"), None)
    assert tls_instance is not None
    assert tls_instance["proxy_type"] == "tls_tunnel"
    assert tls_instance["port"] == test_port
    assert tls_instance["forward_address"] == "vpn.test.com:1194"
    assert tls_instance["cover_domain"] == "cover.test.com"
    assert tls_instance["https_enabled"] is False
    assert tls_instance["dpi_prevention"] is False


# ---------------------------------------------------------------------------
# PATCH /api/instances/{name} — update tls_tunnel settings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_tls_tunnel_forward_address_e2e(app_with_manager, test_port):
    """PATCH should update forward_address and cover_domain for a tls_tunnel instance."""
    # Create tls_tunnel instance
    await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "tls-update-test",
            "port": test_port,
            "proxy_type": "tls_tunnel",
            "forward_address": "old-vpn:1194",
            "cover_domain": "old.example.com",
        },
    )

    # Update forward_address and cover_domain
    resp = await call_handler(
        app_with_manager,
        "PATCH",
        "/api/instances/tls-update-test",
        json_data={
            "forward_address": "new-vpn:2194",
            "cover_domain": "new.example.com",
        },
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "updated"

    # Verify updated values
    resp = await call_handler(app_with_manager, "GET", "/api/instances")
    data = await resp.json()
    tls_instance = next((i for i in data["instances"] if i["name"] == "tls-update-test"), None)
    assert tls_instance is not None
    assert tls_instance["forward_address"] == "new-vpn:2194"
    assert tls_instance["cover_domain"] == "new.example.com"


# ---------------------------------------------------------------------------
# GET /api/instances/{name}/ovpn-snippet
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_ovpn_snippet_tls_tunnel_e2e(app_with_manager, test_port):
    """GET ovpn-snippet for a tls_tunnel instance should return TLS tunnel snippet."""
    await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "tls-snippet-test",
            "port": test_port,
            "proxy_type": "tls_tunnel",
            "forward_address": "vpn.snippet.com:1194",
        },
    )

    resp = await call_handler(
        app_with_manager,
        "GET",
        "/api/instances/tls-snippet-test/ovpn-snippet",
    )
    assert resp.status == 200
    text = await resp.text()
    assert "TLS Tunnel" in text
    assert "tls-crypt" in text
    assert str(test_port) in text


@pytest.mark.asyncio
async def test_get_ovpn_snippet_squid_e2e(app_with_manager, test_port):
    """GET ovpn-snippet for a squid instance should return squid-style snippet."""
    await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "squid-snippet-test",
            "port": test_port,
        },
    )

    resp = await call_handler(
        app_with_manager,
        "GET",
        "/api/instances/squid-snippet-test/ovpn-snippet",
    )
    assert resp.status == 200
    text = await resp.text()
    assert "Squid Proxy" in text
    assert "http-proxy" in text
    assert str(test_port) in text


@pytest.mark.asyncio
async def test_get_ovpn_snippet_not_found_e2e(app_with_manager):
    """GET ovpn-snippet for non-existent instance should return 404."""
    resp = await call_handler(
        app_with_manager,
        "GET",
        "/api/instances/does-not-exist/ovpn-snippet",
    )
    assert resp.status == 404


# ---------------------------------------------------------------------------
# User management returns 400 for tls_tunnel instances
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_user_tls_tunnel_returns_400_e2e(app_with_manager, test_port):
    """POST /api/instances/{name}/users for tls_tunnel should return 400."""
    await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "tls-users-test",
            "port": test_port,
            "proxy_type": "tls_tunnel",
            "forward_address": "vpn:1194",
        },
    )

    resp = await call_handler(
        app_with_manager,
        "POST",
        "/api/instances/tls-users-test/users",
        json_data={"username": "user1", "password": "password123"},
    )
    assert resp.status == 400
    data = await resp.json()
    assert "error" in data
    assert "tls_tunnel" in data["error"]


@pytest.mark.asyncio
async def test_get_users_tls_tunnel_returns_400_e2e(app_with_manager, test_port):
    """GET /api/instances/{name}/users for tls_tunnel should return 400."""
    await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "tls-getusers-test",
            "port": test_port,
            "proxy_type": "tls_tunnel",
            "forward_address": "vpn:1194",
        },
    )

    resp = await call_handler(
        app_with_manager,
        "GET",
        "/api/instances/tls-getusers-test/users",
    )
    assert resp.status == 400
    data = await resp.json()
    assert "error" in data
    assert "tls_tunnel" in data["error"]


@pytest.mark.asyncio
async def test_remove_user_tls_tunnel_returns_400_e2e(app_with_manager, test_port):
    """DELETE /api/instances/{name}/users/{username} for tls_tunnel should return 400."""
    await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "tls-rmuser-test",
            "port": test_port,
            "proxy_type": "tls_tunnel",
            "forward_address": "vpn:1194",
        },
    )

    resp = await call_handler(
        app_with_manager,
        "DELETE",
        "/api/instances/tls-rmuser-test/users/someuser",
    )
    assert resp.status == 400
    data = await resp.json()
    assert "error" in data
    assert "tls_tunnel" in data["error"]


# ---------------------------------------------------------------------------
# Full lifecycle: create, list, update, snippet, stop, delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tls_tunnel_full_lifecycle_e2e(app_with_manager, test_port):
    """Full lifecycle test: create -> list -> update -> snippet -> stop -> delete."""
    # 1. Create
    resp = await call_handler(
        app_with_manager,
        "POST",
        "/api/instances",
        json_data={
            "name": "tls-lifecycle",
            "port": test_port,
            "proxy_type": "tls_tunnel",
            "forward_address": "vpn.lifecycle.com:1194",
            "cover_domain": "lifecycle.example.com",
        },
    )
    assert resp.status == 201

    # 2. List and verify
    resp = await call_handler(app_with_manager, "GET", "/api/instances")
    data = await resp.json()
    instance = next((i for i in data["instances"] if i["name"] == "tls-lifecycle"), None)
    assert instance is not None
    assert instance["proxy_type"] == "tls_tunnel"
    assert instance["status"] == "running"

    # 3. Update forward_address
    resp = await call_handler(
        app_with_manager,
        "PATCH",
        "/api/instances/tls-lifecycle",
        json_data={"forward_address": "updated-vpn:2194"},
    )
    assert resp.status == 200

    # 4. Get OVPN snippet
    resp = await call_handler(
        app_with_manager,
        "GET",
        "/api/instances/tls-lifecycle/ovpn-snippet",
    )
    assert resp.status == 200
    text = await resp.text()
    assert "TLS Tunnel" in text

    # 5. Stop instance
    resp = await call_handler(
        app_with_manager,
        "POST",
        "/api/instances/tls-lifecycle/stop",
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "stopped"

    # 6. Delete instance
    resp = await call_handler(
        app_with_manager,
        "DELETE",
        "/api/instances/tls-lifecycle",
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "removed"
