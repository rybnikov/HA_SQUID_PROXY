"""E2E tests for validation - forward_address port normalization.

Tests verify that forward_address without port is accepted and normalized.
Other validation tests are covered by unit/integration tests.
"""

import pytest

from tests.e2e.utils import (
    ADDON_URL,
    create_instance_via_api,
    delete_instance_via_api,
    fill_textfield_by_testid,
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_forward_address_optional_port_accepted(
    browser, unique_name, unique_port, api_session
):
    """Test that forward_address without port is accepted (defaults to 443)."""
    instance_name = unique_name("optional-port")
    port = unique_port(3200)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Open create form
        try:
            await page.click('[data-testid="add-instance-button"]', timeout=2000)
        except Exception:
            await page.click('[data-testid="empty-state-add-button"]')
        await page.wait_for_selector(
            '[data-testid="create-instance-form"]', timeout=30000
        )

        # Select TLS Tunnel
        await page.click('[data-testid="proxy-type-tls-tunnel"]')
        await page.wait_for_timeout(500)

        # Fill form with forward_address WITHOUT port
        await fill_textfield_by_testid(page, "create-name-input", instance_name)
        await fill_textfield_by_testid(page, "create-port-input", str(port))
        await fill_textfield_by_testid(
            page, "create-forward-address-input", "vpn.example.com"
        )

        # Submit should succeed
        await page.click('[data-testid="create-submit-button"]')
        await page.wait_for_timeout(2000)

        # Verify instance was created
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instances = data.get("instances", [])
            instance = next(
                (i for i in instances if i["name"] == instance_name), None
            )
            assert instance is not None, f"Instance {instance_name} should be created"
            # Backend should normalize to include :443
            assert (
                instance.get("forward_address") == "vpn.example.com:443"
            ), "Should normalize forward_address to include default port 443"
    finally:
        await delete_instance_via_api(api_session, instance_name)
        await page.close()
