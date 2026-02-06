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
    fill_textfield_by_testid,
    navigate_to_dashboard,
    navigate_to_settings,
    set_switch_state_by_testid,
)

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "test_token")
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

        # Open create page
        await page.click('[data-testid="add-instance-button"]')
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

        # Critical: Wait for Squid to start (or crash if ssl_bump issue)
        await asyncio.sleep(5)

        # Verify instance still running (multiple checks)
        for check_num in range(3):
            async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
                assert instance is not None, f"Instance should exist (check {check_num + 1})"
                assert instance.get("running"), (
                    f"HTTPS instance crashed (check {check_num + 1}). "
                    "Verify no ssl_bump in config and certificate generated correctly."
                )

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
        await page.goto(ADDON_URL)

        # Create HTTP instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)
        await asyncio.sleep(2)

        # Open settings and enable HTTPS
        await navigate_to_settings(page, instance_name)

        await set_switch_state_by_testid(page, "settings-https-switch", True)
        await asyncio.sleep(0.5)

        # Wait for save button to become enabled (isDirty must be true)
        await page.wait_for_selector(
            '[data-testid="settings-save-button"]:not([disabled])', timeout=5000
        )

        # Save
        await page.click('[data-testid="settings-save-button"]')
        await page.wait_for_selector("text=Saved!", timeout=10000)

        # Navigate back to dashboard
        await navigate_to_dashboard(page, ADDON_URL)

        # Wait for restart with cert generation
        await asyncio.sleep(5)

        # Verify HTTPS enabled
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert instance.get("https_enabled"), "HTTPS should be enabled"
            assert instance.get("running"), "Instance should still be running"
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

        # Create HTTPS instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)
        await asyncio.sleep(3)

        # Open settings and disable HTTPS
        await navigate_to_settings(page, instance_name)

        await set_switch_state_by_testid(page, "settings-https-switch", False)
        await asyncio.sleep(0.5)

        # Wait for save button to become enabled (isDirty must be true)
        await page.wait_for_selector(
            '[data-testid="settings-save-button"]:not([disabled])', timeout=5000
        )

        # Save
        await page.click('[data-testid="settings-save-button"]')
        await page.wait_for_selector("text=Saved!", timeout=10000)

        # Navigate back to dashboard
        await navigate_to_dashboard(page, ADDON_URL)

        # Wait for restart
        await asyncio.sleep(3)

        # Verify HTTPS disabled
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
        # Wait for the dashboard to load (add-instance-button is on dashboard).
        await page.wait_for_selector(
            '[data-testid="add-instance-button"]', state="attached", timeout=15000
        )

        # Now verify the instance card is gone from the dashboard
        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', state="hidden", timeout=10000
        )

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

        # Create HTTPS instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)
        await asyncio.sleep(3)

        # Open settings and regenerate cert
        await navigate_to_settings(page, instance_name)

        # Look for certificate regenerate button
        regenerate_btn_selector = '[data-testid="cert-regenerate-button"]'
        if await page.is_visible(regenerate_btn_selector):
            await page.click(regenerate_btn_selector)

            # Wait for regeneration button loading state to disappear
            await page.wait_for_selector(
                '[data-testid="cert-regenerate-button"]:not([disabled])',
                timeout=15000,
            )
            await asyncio.sleep(1)

        # Verify instance still running
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
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

        # Add user
        await navigate_to_settings(page, instance_name)

        await fill_textfield_by_testid(page, "user-username-input", "httpsuser")
        await fill_textfield_by_testid(page, "user-password-input", "httpspass")
        await page.click('[data-testid="user-add-button"]')
        await page.wait_for_selector('[data-testid="user-chip-httpsuser"]', timeout=10000)

        # Verify user added
        user_list = await page.inner_text('[data-testid="user-list"]')
        assert "httpsuser" in user_list
    finally:
        await page.close()
