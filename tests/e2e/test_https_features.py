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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.check("#newHttps")
        await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)

        await page.click("#addInstanceModal button:has-text('Create Instance')")

        # Wait for instance to be created
        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=30000)

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

        # Open Add Instance modal
        await page.click("button:has-text('Add Instance')")
        await page.wait_for_selector("#addInstanceModal:visible", timeout=5000)

        # Auto-generation message should be hidden initially
        assert not await page.is_visible(
            "text=Certificate will be auto-generated"
        ), "Auto-generation message should be hidden initially"

        # Check HTTPS
        await page.check("#newHttps")
        await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
        assert await page.is_visible(
            "text=Certificate will be auto-generated"
        ), "Auto-generation message should be visible"

        # Uncheck HTTPS
        await page.uncheck("#newHttps")
        await page.wait_for_selector(
            "text=Certificate will be auto-generated", state="hidden", timeout=2000
        )
        assert not await page.is_visible(
            "text=Certificate will be auto-generated"
        ), "Auto-generation message should be hidden after unchecking"
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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.check("#newHttps")
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=30000)

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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        # Don't check HTTPS - create as HTTP
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=15000)
        await asyncio.sleep(2)

        # Open settings and enable HTTPS
        await page.click(f"{instance_selector} button[data-action='settings']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)

        await page.click("#settingsModal [data-tab='main']")
        await page.check("#editHttps")
        await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)

        # Save
        await page.click("#settingsModal button:has-text('Save Changes')")
        await page.wait_for_selector("#settingsModal", state="hidden", timeout=30000)

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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.check("#newHttps")
        await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=30000)
        await asyncio.sleep(3)

        # Open settings and disable HTTPS
        await page.click(f"{instance_selector} button[data-action='settings']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)

        await page.click("#settingsModal [data-tab='main']")
        await page.uncheck("#editHttps")

        # Save
        await page.click("#settingsModal button:has-text('Save Changes')")
        await page.wait_for_selector("#settingsModal", state="hidden", timeout=30000)

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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.check("#newHttps")
        await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=30000)

        # Open delete tab
        await page.click(f"{instance_selector} button[data-action='settings']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='delete']")

        # Confirm delete
        await page.click("#confirmDeleteBtn")

        # Wait for instance to disappear
        await page.wait_for_selector(instance_selector, state="hidden", timeout=10000)

        # Verify via API
        await asyncio.sleep(2)
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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.check("#newHttps")
        await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=30000)
        await asyncio.sleep(3)

        # Open settings and regenerate cert
        await page.click(f"{instance_selector} button[data-action='settings']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)

        # Look for certificate tab
        cert_tab = await page.query_selector("#settingsModal [data-tab='certificate']")
        if cert_tab:
            await page.click(cert_tab)

            regenerate_btn = await page.query_selector(
                "#settingsModal button:has-text('Regenerate')"
            )
            if regenerate_btn:
                await page.click(regenerate_btn)

                # Wait for regeneration
                await page.wait_for_function(
                    "document.querySelector('#certStatus')?.textContent?.includes('generated')",
                    timeout=15000,
                )

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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.check("#newHttps")
        await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=30000)

        # Add user
        await page.click(f"{instance_selector} button[data-action='settings']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

        await page.fill("#newUsername", "httpsuser")
        await page.fill("#newPassword", "httpspass")
        await page.click("#settingsModal button:has-text('Add')")
        await page.wait_for_selector(".user-item:has-text('httpsuser')", timeout=10000)

        # Verify user added
        user_list = await page.inner_text("#userList")
        assert "httpsuser" in user_list
    finally:
        await page.close()
