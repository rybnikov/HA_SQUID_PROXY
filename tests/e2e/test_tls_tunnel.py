"""E2E tests for TLS Tunnel proxy type.

Covers the full TLS Tunnel lifecycle:
1. Create TLS Tunnel via UI (proxy type selection, VPN address, cover domain)
2. Dashboard displays TLS Tunnel badge, shield icon, and forward address
3. Settings page shows TLS-specific tabs (Connection Info, Cover Site)
4. Settings page hides Squid-specific tabs (Users, HTTPS, Test Connectivity)
5. Connection Info tab shows DPI evasion, port, VPN server, .ovpn snippet, How it works
6. Cover Site tab shows cover domain input and SSL cert status
7. Update forward_address and cover_domain via GeneralTab settings
8. Start/stop lifecycle
9. Delete TLS Tunnel instance
10. Proxy type selector UI toggle behavior on create page
11. Mixed Squid + TLS Tunnel dashboard coexistence

All tests are designed for parallel execution with pytest-xdist (-n auto).
Uses per-test fixtures and worker-scoped port allocation to avoid conflicts.
"""

import asyncio
import os

import pytest

from tests.e2e.utils import (
    create_instance_via_ui,
    create_tls_tunnel_via_ui,
    fill_textfield_by_testid,
    navigate_to_dashboard,
    navigate_to_settings,
    wait_for_addon_healthy,
    wait_for_instance_running,
    wait_for_instance_stopped,
)

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "dev_token")
API_HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_create_tls_tunnel_instance(browser, unique_name, unique_port, api_session):
    """Create a TLS Tunnel instance through the UI with all fields.

    Verifies:
    - TLS Tunnel proxy type selector works
    - VPN Server Address and Cover Domain fields appear
    - Instance is created and appears on dashboard
    - API reports correct proxy_type, forward_address, cover_domain
    """
    instance_name = unique_name("tls-create")
    port = unique_port(8443)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.example.com:1194",
            cover_domain="cover.example.com",
        )

        # Verify instance card is visible on dashboard
        card = page.locator(f'[data-testid="instance-card-{instance_name}"]')
        await card.wait_for(state="visible", timeout=10000)

        # Verify via API
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None, f"Instance {instance_name} should exist"
            assert instance.get("proxy_type") == "tls_tunnel", "Should be tls_tunnel type"
            assert instance.get("forward_address") == "vpn.example.com:1194"
            assert instance.get("cover_domain") == "cover.example.com"
            assert instance.get("port") == port
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tls_tunnel_dashboard_display(browser, unique_name, unique_port, api_session):
    """Dashboard shows TLS Tunnel badge, shield icon, and forward address.

    Verifies:
    - The instance card shows a 'TLS Tunnel' badge text
    - The shield-lock-outline icon is used (not server-network)
    - The forward_address is shown below the port as "-> vpn..."
    """
    instance_name = unique_name("tls-badge")
    port = unique_port(8444)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.test.com:443",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Verify TLS Tunnel badge is visible on the card
        card = page.locator(f'[data-testid="instance-card-{instance_name}"]')
        badge_text = await card.inner_text()
        assert (
            "TLS Tunnel" in badge_text
        ), f"Card should display 'TLS Tunnel' badge, got: {badge_text}"

        # Verify forward address is displayed on the card
        expected_addr = "vpn.test.com" + ":443"
        assert (
            expected_addr in badge_text
        ), f"Card should display forward address, got: {badge_text}"

        # Verify the shield-lock-outline icon is used
        # Check both ha-icon custom element (HA mode) and span[data-icon] fallback (standalone)
        has_shield = await card.evaluate(
            """(el) => {
                const haIcons = el.querySelectorAll('ha-icon');
                if (Array.from(haIcons).some(i => i.icon === 'mdi:shield-lock-outline')) return true;
                const spans = el.querySelectorAll('span[data-icon]');
                return Array.from(spans).some(s => s.getAttribute('data-icon') === 'mdi:shield-lock-outline');
            }"""
        )
        assert has_shield, "TLS Tunnel card should use shield-lock-outline icon"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tls_tunnel_settings_conditional_tabs(browser, unique_name, unique_port, api_session):
    """TLS Tunnel settings page shows Connection Info and Cover Site, hides Squid tabs.

    Verifies:
    - Configuration card (GeneralTab) is present with VPN Server Address field
    - Connection Info card is visible
    - Cover Site card is visible
    - Proxy Users card is NOT visible (Squid-only)
    - Test Connectivity card is NOT visible (Squid-only)
    - HTTPS switch is NOT visible (Squid-only)
    """
    instance_name = unique_name("tls-tabs")
    port = unique_port(8445)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.example.com:1194",
            cover_domain="example.com",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Navigate to settings
        await navigate_to_settings(page, instance_name)

        # TLS-specific elements SHOULD be visible
        # Connection Info card contains the ovpn snippet
        ovpn_snippet = page.locator('[data-testid="ovpn-snippet-content"]')
        await ovpn_snippet.wait_for(state="visible", timeout=10000)

        # Cover Site card contains the cover domain input
        cover_input = page.locator('[data-testid="cover-domain-input"]')
        assert await cover_input.count() > 0, "Cover domain input should be visible"

        # VPN Server Address field in GeneralTab
        forward_input = page.locator('[data-testid="settings-forward-address-input"]')
        assert await forward_input.count() > 0, "Forward address input should be visible"

        # Squid-specific elements should NOT be visible
        https_switch = page.locator('[data-testid="settings-https-switch"]')
        assert await https_switch.count() == 0, "HTTPS switch should not be visible for TLS tunnel"

        dpi_switch = page.locator('[data-testid="settings-dpi-switch"]')
        assert await dpi_switch.count() == 0, "DPI switch should not be visible for TLS tunnel"

        # "Proxy Users" card title should not be present
        page_text = await page.inner_text("body")
        assert (
            "Proxy Users" not in page_text
        ), "Proxy Users card should NOT be visible for TLS Tunnel"

        # "Test Connectivity" card title should not be present
        assert (
            "Test Connectivity" not in page_text
        ), "Test Connectivity card should NOT be visible for TLS Tunnel"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tls_tunnel_connection_info_tab(browser, unique_name, unique_port, api_session):
    """Connection Info tab displays DPI evasion, listen port, VPN server, .ovpn snippet, and How it works.

    Verifies:
    - DPI evasion level indicator is shown
    - Listen port is displayed
    - VPN server address is displayed
    - OpenVPN configuration snippet is loaded and visible
    - Copy button is present
    - Collapsible "How it works" section exists
    """
    instance_name = unique_name("tls-conninfo")
    port = unique_port(8446)
    vpn_address = "vpn.example.com:1194"

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address=vpn_address,
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        await navigate_to_settings(page, instance_name)

        # Wait for the OpenVPN snippet to load
        snippet_el = page.locator('[data-testid="ovpn-snippet-content"]')
        await snippet_el.wait_for(state="visible", timeout=10000)

        # Snippet should contain meaningful content (not just "Loading...")
        snippet_text = await snippet_el.inner_text()
        assert snippet_text, "OpenVPN snippet should not be empty"
        assert snippet_text != "Loading...", "OpenVPN snippet should have loaded"

        # Copy button should be present
        copy_btn = page.locator('[data-testid="copy-ovpn-snippet"]')
        assert await copy_btn.count() > 0, "Copy snippet button should be visible"

        # Verify the settings page content
        page_text = await page.inner_text("body")

        # DPI evasion level should be shown
        assert "DPI Evasion" in page_text, "Connection Info should show DPI evasion level"

        # Listen port should be displayed
        assert str(port) in page_text, f"Page should display port {port}"

        # VPN server address should be displayed
        assert vpn_address in page_text, f"Page should display VPN address {vpn_address}"

        # "How it works" collapsible section should exist
        how_it_works = page.locator("text=How it works")
        assert (
            await how_it_works.count() > 0
        ), "Connection Info should have a 'How it works' collapsible section"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tls_tunnel_cover_site_tab(browser, unique_name, unique_port, api_session):
    """Cover Site tab shows cover domain input field and SSL certificate status.

    Verifies:
    - Cover domain input is visible and editable
    - SSL certificate status is displayed
    - Save button is disabled when no changes made
    - Save button enables after editing cover domain
    - Saving updates the cover domain via API
    """
    instance_name = unique_name("tls-cover")
    port = unique_port(8447)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.example.com:1194",
            cover_domain="original.example.com",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        await navigate_to_settings(page, instance_name)

        # Find the cover domain input in the Cover Site card
        cover_input = page.locator('[data-testid="cover-domain-input"]')
        await cover_input.wait_for(state="visible", timeout=10000)

        # Verify SSL certificate status is displayed
        page_text = await page.inner_text("body")
        assert (
            "SSL Certificate" in page_text
        ), "Cover Site tab should display SSL certificate status"

        # Save button should be disabled initially (no changes)
        save_btn = page.locator('[data-testid="cover-site-save-button"]')
        is_disabled = await save_btn.is_disabled()
        assert is_disabled, "Cover site save button should be disabled when no changes are made"

        # Change the cover domain
        await fill_textfield_by_testid(page, "cover-domain-input", "updated.example.com")
        await asyncio.sleep(0.5)

        # Save button should now be enabled
        await page.wait_for_selector(
            '[data-testid="cover-site-save-button"]:not([disabled])', timeout=5000
        )

        # Click save
        await page.click('[data-testid="cover-site-save-button"]')
        await asyncio.sleep(2)

        # Verify via API
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert (
                instance.get("cover_domain") == "updated.example.com"
            ), f"Cover domain should be updated, got: {instance.get('cover_domain')}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_update_tls_tunnel_settings(browser, unique_name, unique_port, api_session):
    """Update forward_address and cover_domain via GeneralTab settings, verify via API.

    Steps:
    1. Create TLS tunnel instance with initial values
    2. Open settings
    3. Change forward_address in GeneralTab
    4. Change cover_domain in GeneralTab
    5. Save changes via GeneralTab save button
    6. Verify API reflects both updated values
    """
    instance_name = unique_name("tls-update")
    port = unique_port(8448)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.old.com:1194",
            cover_domain="old.example.com",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        await navigate_to_settings(page, instance_name)

        # Update the forward address field in GeneralTab
        await fill_textfield_by_testid(page, "settings-forward-address-input", "vpn.new.com:443")

        # Update the cover domain field in GeneralTab
        await fill_textfield_by_testid(page, "settings-cover-domain-input", "new.example.com")
        await asyncio.sleep(0.5)

        # Save button should be enabled after changes
        await page.wait_for_selector(
            '[data-testid="settings-save-button"]:not([disabled])', timeout=5000
        )

        # Save changes
        await page.click('[data-testid="settings-save-button"]')
        await page.wait_for_selector("text=Saved!", timeout=10000)

        # Allow time for the update to propagate
        await asyncio.sleep(3)

        # Verify both fields updated via API
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert instance.get("forward_address") == "vpn.new.com:443", (
                f"forward_address should be updated to 'vpn.new.com:443', "
                f"got: {instance.get('forward_address')}"
            )
            assert instance.get("cover_domain") == "new.example.com", (
                f"cover_domain should be updated to 'new.example.com', "
                f"got: {instance.get('cover_domain')}"
            )
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tls_tunnel_start_stop(browser, unique_name, unique_port, api_session):
    """Start and stop a TLS Tunnel instance via dashboard controls.

    Verifies:
    - Instance starts running after creation
    - Stop button stops the instance
    - Start button restarts the instance
    - Instance state transitions are reflected in API
    """
    instance_name = unique_name("tls-startstop")
    port = unique_port(8449)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.example.com:1194",
        )

        # Verify running after creation
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Stop instance
        await page.click(f'[data-testid="instance-stop-chip-{instance_name}"]')
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Verify stopped via API
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert not instance.get("running"), "Instance should be stopped"

        # Start instance again
        await page.click(f'[data-testid="instance-start-chip-{instance_name}"]')
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Verify running via API
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert instance.get("running"), "Instance should be running after restart"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_delete_tls_tunnel(browser, unique_name, unique_port, api_session):
    """Delete a TLS Tunnel instance via the settings danger zone.

    Verifies:
    - Delete button opens confirmation dialog
    - Confirming delete removes the instance
    - Instance card disappears from dashboard
    - API no longer returns the instance
    """
    instance_name = unique_name("tls-delete")
    port = unique_port(8450)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.example.com:1194",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Open settings
        await navigate_to_settings(page, instance_name)

        # Click delete button in Danger Zone
        await page.click('[data-testid="settings-delete-button"]')

        # Confirm delete in dialog
        await page.wait_for_selector('[data-testid="delete-confirm-button"]', timeout=5000)
        await page.click('[data-testid="delete-confirm-button"]')

        # Wait for deletion to complete by checking API
        for _attempt in range(30):
            async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instances = data.get("instances", []) if isinstance(data, dict) else data
                if not any(i["name"] == instance_name for i in instances):
                    break
            await asyncio.sleep(1)
        else:
            pytest.fail(f"TLS Tunnel instance {instance_name} was not deleted after 30 seconds")

        # Navigate to dashboard and verify card is gone
        await navigate_to_dashboard(page, ADDON_URL)
        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', state="hidden", timeout=5000
        )
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_proxy_type_selector_ui(browser, unique_name, unique_port, api_session):
    """Verify proxy type selector toggles form fields correctly on the create page.

    Steps:
    1. Navigate to create page
    2. Verify Squid is selected by default (HTTPS switch visible; forward_address hidden)
    3. Switch to TLS Tunnel (forward_address appears; HTTPS, Users card hidden)
    4. Switch back to Squid (original fields return, TLS fields disappear)
    """
    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Navigate to create page (try FAB first, fallback to empty state)
        try:
            await page.click('[data-testid="add-instance-button"]', timeout=2000)
        except Exception:
            await page.click('[data-testid="empty-state-add-button"]')
        await page.wait_for_selector('[data-testid="create-name-input"]', timeout=10000)

        # --- Squid is default ---
        # HTTPS switch should be visible
        https_switch = page.locator('[data-testid="create-https-switch"]')
        assert (
            await https_switch.count() > 0
        ), "HTTPS switch should be visible when Squid is selected"

        # Forward address should NOT be visible
        fwd_input = page.locator('[data-testid="create-forward-address-input"]')
        assert (
            await fwd_input.count() == 0
        ), "Forward address input should NOT be visible when Squid is selected"

        # Cover domain should NOT be visible
        cover_input = page.locator('[data-testid="create-cover-domain-input"]')
        assert (
            await cover_input.count() == 0
        ), "Cover domain input should NOT be visible when Squid is selected"

        # --- Switch to TLS Tunnel ---
        await page.click('[data-testid="proxy-type-tls-tunnel"]')
        await asyncio.sleep(0.5)

        # Forward address should now be visible
        fwd_input = page.locator('[data-testid="create-forward-address-input"]')
        assert (
            await fwd_input.count() > 0
        ), "Forward address input should be visible when TLS Tunnel is selected"

        # Cover domain input should be visible
        cover_input = page.locator('[data-testid="create-cover-domain-input"]')
        assert (
            await cover_input.count() > 0
        ), "Cover domain input should be visible when TLS Tunnel is selected"

        # HTTPS switch should NOT be visible
        https_switch = page.locator('[data-testid="create-https-switch"]')
        assert (
            await https_switch.count() == 0
        ), "HTTPS switch should NOT be visible when TLS Tunnel is selected"

        # Initial Users card should NOT be visible (Squid-only)
        user_username = page.locator('[data-testid="create-user-username-input"]')
        assert (
            await user_username.count() == 0
        ), "User inputs should NOT be visible when TLS Tunnel is selected"

        # --- Switch back to Squid ---
        await page.click('[data-testid="proxy-type-squid"]')
        await asyncio.sleep(0.5)

        # HTTPS switch should return
        https_switch = page.locator('[data-testid="create-https-switch"]')
        assert (
            await https_switch.count() > 0
        ), "HTTPS switch should return when switching back to Squid"

        # Forward address should disappear
        fwd_input = page.locator('[data-testid="create-forward-address-input"]')
        assert (
            await fwd_input.count() == 0
        ), "Forward address input should disappear when switching back to Squid"

        # Cover domain should disappear
        cover_input = page.locator('[data-testid="create-cover-domain-input"]')
        assert (
            await cover_input.count() == 0
        ), "Cover domain input should disappear when switching back to Squid"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_mixed_squid_and_tls_tunnel(browser, unique_name, unique_port, api_session):
    """Create both a Squid and a TLS Tunnel instance, verify both coexist on dashboard.

    Verifies:
    - Both instance cards are visible on dashboard
    - Squid card uses server-network icon and has no TLS Tunnel badge
    - TLS Tunnel card uses shield-lock-outline icon and has TLS Tunnel badge
    - API reports correct proxy_type for each instance
    """
    squid_name = unique_name("mixed-squid")
    tunnel_name = unique_name("mixed-tunnel")
    squid_port = unique_port(3230)
    tunnel_port = unique_port(8451)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create Squid instance
        await create_instance_via_ui(page, ADDON_URL, squid_name, squid_port, https_enabled=False)

        # Create TLS Tunnel instance
        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            tunnel_name,
            tunnel_port,
            forward_address="vpn.mixed.com:1194",
        )

        # Verify both cards are visible
        squid_card = page.locator(f'[data-testid="instance-card-{squid_name}"]')
        tunnel_card = page.locator(f'[data-testid="instance-card-{tunnel_name}"]')
        await squid_card.wait_for(state="visible", timeout=10000)
        await tunnel_card.wait_for(state="visible", timeout=10000)

        # Squid card should NOT have "TLS Tunnel" badge
        squid_text = await squid_card.inner_text()
        assert (
            "TLS Tunnel" not in squid_text
        ), "Squid instance card should NOT show 'TLS Tunnel' badge"

        # TLS Tunnel card should have "TLS Tunnel" badge
        tunnel_text = await tunnel_card.inner_text()
        assert (
            "TLS Tunnel" in tunnel_text
        ), "TLS Tunnel instance card should show 'TLS Tunnel' badge"

        # Verify Squid card uses server-network icon
        # Check both ha-icon custom element (HA mode) and span[data-icon] fallback (standalone)
        has_server_icon = await squid_card.evaluate(
            """(el) => {
                const haIcons = el.querySelectorAll('ha-icon');
                if (Array.from(haIcons).some(i => i.icon === 'mdi:server-network')) return true;
                const spans = el.querySelectorAll('span[data-icon]');
                return Array.from(spans).some(s => s.getAttribute('data-icon') === 'mdi:server-network');
            }"""
        )
        assert has_server_icon, "Squid card should use server-network icon"

        # Verify TLS Tunnel card uses shield-lock-outline icon
        has_shield_icon = await tunnel_card.evaluate(
            """(el) => {
                const haIcons = el.querySelectorAll('ha-icon');
                if (Array.from(haIcons).some(i => i.icon === 'mdi:shield-lock-outline')) return true;
                const spans = el.querySelectorAll('span[data-icon]');
                return Array.from(spans).some(s => s.getAttribute('data-icon') === 'mdi:shield-lock-outline');
            }"""
        )
        assert has_shield_icon, "TLS Tunnel card should use shield-lock-outline icon"

        # Verify both exist via API with correct types
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            squid_inst = next((i for i in data["instances"] if i["name"] == squid_name), None)
            tunnel_inst = next((i for i in data["instances"] if i["name"] == tunnel_name), None)
            assert squid_inst is not None, f"Squid instance {squid_name} should exist"
            assert tunnel_inst is not None, f"TLS Tunnel instance {tunnel_name} should exist"
            assert (
                squid_inst.get("proxy_type", "squid") == "squid"
            ), f"Squid proxy_type should be 'squid', got: {squid_inst.get('proxy_type')}"
            assert (
                tunnel_inst.get("proxy_type") == "tls_tunnel"
            ), f"TLS Tunnel proxy_type should be 'tls_tunnel', got: {tunnel_inst.get('proxy_type')}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tls_tunnel_stays_running_after_creation(
    browser, unique_name, unique_port, api_session
):
    """TLS Tunnel instance stays running after creation (stability check).

    Similar to the HTTPS ssl_bump critical test -- verifies the TLS tunnel
    process does not crash shortly after starting.
    """
    instance_name = unique_name("tls-stable")
    port = unique_port(8452)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        await create_tls_tunnel_via_ui(
            page,
            ADDON_URL,
            instance_name,
            port,
            forward_address="vpn.example.com:1194",
            cover_domain="stable.example.com",
        )

        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Wait and verify instance stays running over several checks
        await asyncio.sleep(5)

        for attempt in range(5):
            await asyncio.sleep(3)
            try:
                async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                    data = await resp.json()
                    instance = next(
                        (i for i in data["instances"] if i["name"] == instance_name), None
                    )
                    assert instance is not None, (
                        f"Instance {instance_name} not found in API (attempt {attempt + 1}). "
                        f"Found: {[i['name'] for i in data.get('instances', [])]}"
                    )
                    assert instance.get("running"), (
                        f"TLS Tunnel crashed after creation (attempt {attempt + 1}). "
                        f"Status: {instance}"
                    )
            except (ConnectionError, OSError):
                # Addon may have restarted, wait for recovery
                await wait_for_addon_healthy(ADDON_URL, api_session, timeout=30000)
    finally:
        await page.close()
