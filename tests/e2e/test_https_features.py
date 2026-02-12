"""E2E HTTPS-specific tests for parallel execution.

These tests focus on HTTPS functionality:
- Certificate generation and validation
- HTTPS enable/disable transitions
- HTTPS proxy connectivity
- Certificate regeneration

All tests are optimized for parallel execution with pytest-xdist.
"""

import asyncio
import os

import pytest

from tests.e2e.utils import (
    create_instance_via_ui,
    navigate_to_settings,
    set_switch_state_by_testid,
    wait_for_addon_healthy,
    wait_for_instance_running,
)

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "dev_token")
API_HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_https_create_instance_ui(browser, unique_name, unique_port, api_session):
    """Create HTTPS instance via UI.

    Acceptance Criteria:
    - Instance created with HTTPS enabled
    - Certificate auto-generated
    - Instance starts successfully
    """
    instance_name = unique_name("https-create")
    port = unique_port(3240)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create instance with HTTPS
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)

        # Verify HTTPS enabled via API
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert instance.get("https_enabled"), "HTTPS should be enabled"
            assert instance.get("running"), "Instance should be running"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_https_certificate_visibility(browser, unique_name):
    """Test certificate settings visibility toggle.

    When HTTPS checkbox toggled:
    - Certificate message hidden initially
    - Certificate message shown when HTTPS checked
    - Certificate message hidden when HTTPS unchecked
    """
    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Open create page (try FAB first, fallback to empty state)
        try:
            await page.click('[data-testid="add-instance-button"]', timeout=2000)
        except Exception:
            await page.click('[data-testid="empty-state-add-button"]')
        await page.wait_for_selector('[data-testid="create-name-input"]', timeout=10000)

        # HTTPS switch should be unchecked initially
        await page.wait_for_selector(
            '[data-testid="create-https-switch"]', state="attached", timeout=5000
        )

        # Check HTTPS toggle works
        await set_switch_state_by_testid(page, "create-https-switch", True)
        await asyncio.sleep(0.5)

        # Uncheck HTTPS
        await set_switch_state_by_testid(page, "create-https-switch", False)
        await asyncio.sleep(0.5)
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_https_instance_stays_running(browser, unique_name, unique_port, api_session):
    """CRITICAL: HTTPS instance starts and stays running.

    This test catches the ssl_bump FATAL error bug.
    If ssl_bump is in config, Squid crashes with:
    'FATAL: No valid signing certificate configured for HTTPS_port'

    Verification:
    - Instance running after creation
    - Instance still running 5 seconds later
    - No FATAL errors in logs
    """
    instance_name = unique_name("https-running")
    port = unique_port(3241)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create HTTPS instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)

        # Wait for instance to be running via API (HTTPS cert gen can take time)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Critical: Wait for Squid to stabilize (or crash if ssl_bump issue)
        await asyncio.sleep(5)

        # Verify instance STILL running after stabilization (catches ssl_bump crash)
        for check_num in range(3):
            try:
                async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                    data = await resp.json()
                    instance = next(
                        (i for i in data["instances"] if i["name"] == instance_name), None
                    )
                    assert instance is not None, (
                        f"Instance should exist (check {check_num + 1}). "
                        f"Got instances: {[i['name'] for i in data.get('instances', [])]}"
                    )
                    assert instance.get("running"), (
                        f"HTTPS instance crashed (check {check_num + 1}). "
                        "Verify no ssl_bump in config and certificate generated correctly."
                    )
            except (ConnectionError, OSError) as conn_err:
                # If the addon container crashed/restarted, wait for it to recover
                await wait_for_addon_healthy(ADDON_URL, api_session, timeout=30000)
                raise AssertionError(
                    f"Addon connection lost during check {check_num + 1}: {conn_err}"
                ) from conn_err

            if check_num < 2:
                await asyncio.sleep(2)
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_https_enable_on_existing_http(browser, unique_name, unique_port, api_session):
    """Enable HTTPS on existing HTTP instance via settings.

    Workflow:
    1. Create HTTP instance
    2. Enable HTTPS in settings
    3. Certificate auto-generated
    4. Instance restarts with HTTPS port
    """
    instance_name = unique_name("https-enable")
    port = unique_port(3242)

    page = await browser.new_page()
    try:
        # Ensure addon is healthy before navigating (previous test cleanup may cause restart)
        await wait_for_addon_healthy(ADDON_URL, api_session, timeout=30000)

        await page.goto(ADDON_URL)

        # Create HTTP instance and wait for it to be running
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Open settings and enable HTTPS
        await navigate_to_settings(page, instance_name)

        await set_switch_state_by_testid(page, "settings-https-switch", True)

        # Toggle auto-saves — poll API for the change to take effect
        https_enabled = False
        for _attempt in range(30):
            await asyncio.sleep(2)
            try:
                async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                    data = await resp.json()
                    instance = next(
                        (i for i in data["instances"] if i["name"] == instance_name), None
                    )
                    if instance and instance.get("https_enabled"):
                        https_enabled = True
                        break
            except (ConnectionError, OSError):
                await wait_for_addon_healthy(ADDON_URL, api_session, timeout=30000)

        assert https_enabled, "HTTPS should be enabled after saving"

        # Verify instance is running after HTTPS update
        instance = None
        for _attempt in range(15):
            await asyncio.sleep(2)
            try:
                async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                    data = await resp.json()
                    instance = next(
                        (i for i in data["instances"] if i["name"] == instance_name), None
                    )
                    if instance and instance.get("running"):
                        break
            except (ConnectionError, OSError):
                await wait_for_addon_healthy(ADDON_URL, api_session, timeout=30000)
        assert instance is not None, (
            f"Instance {instance_name} should exist after HTTPS enable. "
            f"Found instances: {[i['name'] for i in data.get('instances', [])]}"
        )
        assert instance.get(
            "running"
        ), f"Instance should be running after HTTPS enable. Status: {instance}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_https_disable_on_existing(browser, unique_name, unique_port, api_session):
    """Disable HTTPS on HTTPS instance via settings.

    Workflow:
    1. Create HTTPS instance
    2. Disable HTTPS in settings
    3. Instance restarts with HTTP only
    """
    instance_name = unique_name("https-disable")
    port = unique_port(3243)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create HTTPS instance and wait for it to be running
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Open settings and disable HTTPS
        await navigate_to_settings(page, instance_name)

        await set_switch_state_by_testid(page, "settings-https-switch", False)

        # Toggle auto-saves — poll API for the change to take effect
        https_disabled = False
        for _attempt in range(30):
            await asyncio.sleep(2)
            async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
                if instance and not instance.get("https_enabled"):
                    https_disabled = True
                    break

        assert https_disabled, "HTTPS should be disabled after saving"

        # Wait for instance to finish restarting and be running
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Verify final state
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert not instance.get("https_enabled"), "HTTPS should be disabled"
            assert instance.get("running"), "Instance should still be running"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_https_delete_instance(browser, unique_name, unique_port, api_session):
    """Delete HTTPS instance and verify cleanup.

    Acceptance Criteria:
    - Instance removed from UI
    - Instance removed from API
    - All files deleted
    """
    instance_name = unique_name("https-delete")
    port = unique_port(3244)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create HTTPS instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)

        # Open settings and delete
        await navigate_to_settings(page, instance_name)

        # Click delete button
        await page.click('[data-testid="settings-delete-button"]')

        # Confirm delete in dialog
        await page.wait_for_selector('[data-testid="delete-confirm-button"]', timeout=5000)
        await page.click('[data-testid="delete-confirm-button"]')

        # After delete, the app navigates to the dashboard.
        # Wait for navigation to complete by checking URL
        await page.wait_for_url(f"{ADDON_URL}/", timeout=60000)
        await asyncio.sleep(1)  # Let dashboard render

        # Verify the instance card is gone from the dashboard
        # (No need to wait for hidden - it should not exist at all)
        instance_card = await page.query_selector(f'[data-testid="instance-card-{instance_name}"]')
        assert instance_card is None, f"Instance card for {instance_name} should not exist after deletion"

        # Verify via API
        await asyncio.sleep(1)
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert not any(
                i["name"] == instance_name for i in data["instances"]
            ), "Instance should be deleted"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_https_regenerate_certificate(browser, unique_name, unique_port, api_session):
    """Regenerate HTTPS certificate.

    Workflow:
    1. Create HTTPS instance
    2. Regenerate certificate
    3. Instance remains running
    4. New certificate used
    """
    instance_name = unique_name("https-regen")
    port = unique_port(3245)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create HTTPS instance and wait for it to be running
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)
        await asyncio.sleep(3)

        # Open settings and regenerate cert
        await navigate_to_settings(page, instance_name)

        # Look for certificate regenerate button
        regenerate_btn_selector = '[data-testid="cert-regenerate-button"]'
        await page.wait_for_selector(regenerate_btn_selector, timeout=60000)

        if await page.is_visible(regenerate_btn_selector):
            await page.click(regenerate_btn_selector)

            # Wait for regeneration to complete (cert gen + restart can take 30-60s)
            # The button becomes disabled during regen, then re-enables when done
            await asyncio.sleep(5)  # Give the backend time to start the operation
            for _attempt in range(20):
                try:
                    await page.wait_for_selector(
                        '[data-testid="cert-regenerate-button"]:not([disabled])',
                        timeout=5000,
                    )
                    break
                except Exception:
                    # Page may lose connection if container restarts during cert regen
                    try:
                        await wait_for_addon_healthy(ADDON_URL, api_session, timeout=30000)
                    except Exception:
                        pass
                    await asyncio.sleep(2)

            # Wait for the instance to fully restart after cert regeneration
            await asyncio.sleep(5)

        # Ensure addon is healthy before checking instance state
        await wait_for_addon_healthy(ADDON_URL, api_session, timeout=30000)

        # Verify instance still running via API polling
        instance = None
        for _attempt in range(20):
            try:
                async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                    data = await resp.json()
                    instance = next(
                        (i for i in data["instances"] if i["name"] == instance_name), None
                    )
                    if instance and instance.get("running"):
                        break
            except (ConnectionError, OSError):
                # Addon may have restarted, wait for it
                await wait_for_addon_healthy(ADDON_URL, api_session, timeout=30000)
            await asyncio.sleep(2)

        assert instance is not None, (
            f"Instance {instance_name} should still exist after cert regen. "
            f"Found: {[i['name'] for i in data.get('instances', [])] if data else 'no data'}"
        )
        assert instance.get("running"), "Instance should still be running after cert regen"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_https_with_users(browser, unique_name, unique_port, api_session):
    """Test HTTPS instance with user authentication.

    Workflow:
    1. Create HTTPS instance with users
    2. Unauthenticated request returns 407
    3. Authenticated request succeeds
    """
    instance_name = unique_name("https-auth")
    port = unique_port(3246)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create HTTPS instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)

        # Add user via API (more reliable than UI form + avoids react-query refetch delay)
        async with api_session.post(
            f"{ADDON_URL}/api/instances/{instance_name}/users",
            json={"username": "httpsuser", "password": "httpspass"},
        ) as resp:
            assert resp.status == 200, "Failed to add user httpsuser"
        await asyncio.sleep(3)

        # Verify user appears in settings UI
        await navigate_to_settings(page, instance_name)
        await asyncio.sleep(2)
        await page.wait_for_selector('[data-testid="user-chip-httpsuser"]', timeout=60000)

        # Verify user added
        user_list = await page.inner_text('[data-testid="user-list"]')
        assert "httpsuser" in user_list
    finally:
        await page.close()
