"""Integration tests for restricted file permissions."""

import asyncio

import pytest


@pytest.mark.asyncio
async def test_instance_file_permissions(proxy_manager, test_instance_name, test_port):
    await proxy_manager.create_instance(
        name=test_instance_name,
        port=test_port,
        https_enabled=True,
        users=[{"username": "user1", "password": "password123"}],
    )
    await asyncio.sleep(1)

    from proxy_manager import CERTS_DIR, CONFIG_DIR, LOGS_DIR

    instance_dir = CONFIG_DIR / test_instance_name
    config_file = instance_dir / "squid.conf"
    passwd_file = instance_dir / "passwd"
    cert_file = CERTS_DIR / test_instance_name / "squid.crt"
    key_file = CERTS_DIR / test_instance_name / "squid.key"
    logs_dir = LOGS_DIR / test_instance_name
    cache_dir = logs_dir / "cache"

    assert oct(instance_dir.stat().st_mode)[-3:] == "750"
    assert oct(config_file.stat().st_mode)[-3:] == "640"
    assert oct(passwd_file.stat().st_mode)[-3:] == "640"
    assert oct(cert_file.stat().st_mode)[-3:] == "640"
    assert oct(key_file.stat().st_mode)[-3:] == "640"
    assert oct(logs_dir.stat().st_mode)[-3:] == "700"
    assert oct(cache_dir.stat().st_mode)[-3:] == "700"
