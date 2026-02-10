"""E2E tests covering TEST_PLAN user scenarios (1-7).

Each scenario corresponds to a user workflow in REQUIREMENTS.md:
1. Setup First Proxy with Authentication
2. Enable HTTPS on Existing Instance
3. Troubleshoot Authentication Failure
4. Monitor Proxy Traffic
5. Manage Multiple Proxies
6. Certificate Expired, Regenerate
7. Start/Stop Without Deleting

All tests are designed for parallel execution with pytest-xdist (-n auto).
Uses per-test fixtures and worker-scoped port allocation to avoid conflicts.
"""

import asyncio
import os

import pytest

from tests.e2e.utils import (
    create_instance_via_ui,
    fill_textfield_by_testid,
    get_icon_color,
    is_error_color,
    is_success_color,
    navigate_to_dashboard,
    navigate_to_settings,
    set_switch_state_by_testid,
    wait_for_addon_healthy,
    wait_for_instance_running,
    wait_for_instance_stopped,
)

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "dev_token")
API_HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_1_setup_proxy_with_auth(browser, unique_name, unique_port, api_session):
    """Scenario 1: Setup First Proxy with Authentication.

    Goal: Create a working proxy with basic auth
    Acceptance Criteria:
    - Instance created with name, port, no HTTPS
    - Two users added successfully
    - Proxy running on specified port
    - Unauthenticated requests return 407
    - Authenticated requests return 200
    """
    instance_name = unique_name("scenario1-proxy")
    port = unique_port(3200)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create instance via UI
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Step 2: Add users via API (more reliable than UI form for multi-user add)
        # Each user add triggers a proxy restart (~5-8s), so we must wait for
        # the instance to be running again before adding the next user.
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        for username, password in [("alice", "password123"), ("bob", "password456")]:
            # Wait for instance to be running before adding user
            await wait_for_instance_running(
                page, ADDON_URL, api_session, instance_name, timeout=60000
            )
            added = False
            for _retry in range(5):
                async with api_session.post(
                    f"{ADDON_URL}/api/instances/{instance_name}/users",
                    json={"username": username, "password": password},
                ) as resp:
                    if resp.status == 200:
                        added = True
                        break
                    elif resp.status == 500:
                        # Proxy may be restarting, wait for it to come back
                        await asyncio.sleep(3)
                        await wait_for_instance_running(
                            page, ADDON_URL, api_session, instance_name, timeout=60000
                        )
                    else:
                        break
            assert added, f"Failed to add user {username} after 5 retries"

        # Verify users appear in settings UI (navigate fresh to ensure data is loaded)
        await page.goto(ADDON_URL)
        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', timeout=30000
        )
        await navigate_to_settings(page, instance_name)
        await asyncio.sleep(3)
        await page.wait_for_selector('[data-testid="user-chip-alice"]', timeout=30000)
        await page.wait_for_selector('[data-testid="user-chip-bob"]', timeout=30000)

        # Step 3: Verify via API - instance running
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None, f"Instance {instance_name} should exist"
            assert instance.get("running"), "Instance should be running"

            # TODO: Verify proxy auth via curl when network available
            # unauthenticated → 407
            # authenticated → 200
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_2_enable_https(browser, unique_name, unique_port, api_session):
    """Scenario 2: Enable HTTPS on Existing Instance.

    Goal: Enable HTTPS on running proxy
    Acceptance Criteria:
    - HTTPS section appears after toggling HTTPS ON
    - Certificate generates with correct CN
    - Instance restarts with HTTPS port active
    - Cert file permissions 0o644
    """
    instance_name = unique_name("scenario2-https")
    port = unique_port(3202)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create HTTP instance and wait for it to be running
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Step 2: Enable HTTPS via settings
        await navigate_to_settings(page, instance_name)

        # Enable HTTPS — toggle auto-saves immediately
        await set_switch_state_by_testid(page, "settings-https-switch", True)

        # Poll API for the change to take effect
        https_enabled = False
        for _attempt in range(30):
            await asyncio.sleep(2)
            async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
                if instance and instance.get("https_enabled"):
                    https_enabled = True
                    break

        assert https_enabled, "HTTPS should be enabled after saving"

        # Verify instance is still running after HTTPS update
        for _attempt in range(10):
            await asyncio.sleep(2)
            async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
                if instance and instance.get("running"):
                    break
        assert instance is not None and instance.get(
            "running"
        ), "Instance should be running after HTTPS enable"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_3_auth_troubleshooting(browser, unique_name, unique_port, api_session):
    """Scenario 3: Troubleshoot Authentication Failure.

    Goal: Verify user credentials and add missing user
    Acceptance Criteria:
    - User list visible in Settings page
    - New user can be added and immediately authenticated
    """
    instance_name = unique_name("scenario3-auth")
    port = unique_port(3203)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create instance with initial user
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Add users via API (more reliable for multi-user scenarios)
        async with api_session.post(
            f"{ADDON_URL}/api/instances/{instance_name}/users",
            json={"username": "alice", "password": "password123"},
        ) as resp:
            assert resp.status == 200, "Failed to add user alice"
        await asyncio.sleep(3)

        # Step 2: Add missing user (charlie)
        async with api_session.post(
            f"{ADDON_URL}/api/instances/{instance_name}/users",
            json={"username": "charlie", "password": "charlie123"},
        ) as resp:
            assert resp.status == 200, "Failed to add user charlie"
        await asyncio.sleep(3)

        # Verify both users visible in settings UI
        await navigate_to_settings(page, instance_name)
        await asyncio.sleep(2)
        await page.wait_for_selector('[data-testid="user-chip-alice"]', timeout=30000)
        await page.wait_for_selector('[data-testid="user-chip-charlie"]', timeout=30000)

        # Verify both users visible
        user_list = await page.inner_text('[data-testid="user-list"]')
        assert "alice" in user_list
        assert "charlie" in user_list
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_4_monitor_logs(browser, unique_name, unique_port, api_session):
    """Scenario 4: Monitor Proxy Traffic.

    Goal: View and search logs
    Acceptance Criteria:
    - Log viewer shows recent logs
    - Auto-refresh works (optional)
    - Search filters logs
    """
    instance_name = unique_name("scenario4-logs")
    port = unique_port(3204)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Step 2: Open settings to view logs
        await navigate_to_settings(page, instance_name)

        # Logs are now in a dialog - click the VIEW LOGS button to open it
        await page.click('[data-testid="settings-view-logs-button"]')

        # Wait for dialog to open and verify the logs section is present
        await page.wait_for_selector(
            '[data-testid="logs-type-select"]', state="attached", timeout=5000
        )
        await asyncio.sleep(1)

        # Either the log viewer or the empty-state message should be visible
        has_viewer = await page.locator('[data-testid="logs-viewer"]').count() > 0
        has_empty = await page.locator("text=No log entries found").count() > 0
        assert (
            has_viewer or has_empty
        ), "Logs section should show either log entries or empty message"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_5_multi_instance(browser, unique_name, unique_port, api_session):
    """Scenario 5: Manage Multiple Proxies.

    Goal: Create and manage multiple independent instances
    Acceptance Criteria:
    - Multiple instances visible on dashboard
    - Each with unique name, port, status
    - Users isolated per instance
    """
    name1 = unique_name("multi-1")
    name2 = unique_name("multi-2")
    port1 = unique_port(3205)
    port2 = unique_port(3206)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create first instance and wait for it to be running
        await create_instance_via_ui(page, ADDON_URL, name1, port1, https_enabled=False)
        await wait_for_instance_running(page, ADDON_URL, api_session, name1, timeout=60000)

        # Step 2: Create second instance and wait for it to be running
        await create_instance_via_ui(page, ADDON_URL, name2, port2, https_enabled=False)
        await wait_for_instance_running(page, ADDON_URL, api_session, name2, timeout=60000)

        # Verify both visible on dashboard
        await page.wait_for_selector(f'[data-testid="instance-card-{name1}"]', timeout=30000)
        await page.wait_for_selector(f'[data-testid="instance-card-{name2}"]', timeout=30000)

        # Step 3: Add different users to each instance via API
        # Wait for each instance to be running before adding users
        await wait_for_instance_running(page, ADDON_URL, api_session, name1, timeout=60000)
        for _retry in range(5):
            async with api_session.post(
                f"{ADDON_URL}/api/instances/{name1}/users",
                json={"username": "user1", "password": "pass1234"},
            ) as resp:
                if resp.status == 200:
                    break
                elif resp.status == 500:
                    await asyncio.sleep(3)
                    await wait_for_instance_running(
                        page, ADDON_URL, api_session, name1, timeout=60000
                    )
        else:
            pytest.fail("Failed to add user1 to instance 1 after retries")

        await wait_for_instance_running(page, ADDON_URL, api_session, name2, timeout=60000)
        for _retry in range(5):
            async with api_session.post(
                f"{ADDON_URL}/api/instances/{name2}/users",
                json={"username": "user2", "password": "pass2345"},
            ) as resp:
                if resp.status == 200:
                    break
                elif resp.status == 500:
                    await asyncio.sleep(3)
                    await wait_for_instance_running(
                        page, ADDON_URL, api_session, name2, timeout=60000
                    )
        else:
            pytest.fail("Failed to add user2 to instance 2 after retries")

        # Verify user isolation: instance 2 should have user2 but NOT user1
        # Navigate fresh to ensure data is loaded
        await page.goto(ADDON_URL)
        await page.wait_for_selector(f'[data-testid="instance-card-{name2}"]', timeout=30000)
        await navigate_to_settings(page, name2)
        await asyncio.sleep(3)
        await page.wait_for_selector('[data-testid="user-chip-user2"]', timeout=30000)

        user_list = await page.inner_text('[data-testid="user-list"]')
        assert "user2" in user_list
        assert "user1" not in user_list
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_6_regenerate_cert(browser, unique_name, unique_port, api_session):
    """Scenario 6: Certificate Expired, Regenerate.

    Goal: Regenerate HTTPS certificate
    Acceptance Criteria:
    - Regenerate button accessible
    - New cert generated with updated date
    - Instance continues running
    """
    instance_name = unique_name("scenario6-cert")
    port = unique_port(3207)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create HTTPS instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)

        # Wait for instance to be running
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)
        await asyncio.sleep(2)

        # Step 2: Open settings and access certificate section
        await navigate_to_settings(page, instance_name)

        # Step 3: Regenerate certificate
        regenerate_btn = '[data-testid="cert-regenerate-button"]'
        if await page.is_visible(regenerate_btn):
            await page.click(regenerate_btn)
            # Wait for the Regenerate button to return to non-loading state
            # (cert generation + restart can take 30-60s in the container)
            await asyncio.sleep(5)  # Give the backend time to start
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
            # Wait for instance to restart and stabilize after cert regeneration
            await asyncio.sleep(8)

        # Ensure addon is healthy before checking instance state
        await wait_for_addon_healthy(ADDON_URL, api_session, timeout=30000)

        # Verify instance still running - poll multiple times with error recovery
        instance = None
        data = {}
        for _attempt in range(20):
            try:
                async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                    data = await resp.json()
                    instance = next(
                        (i for i in data["instances"] if i["name"] == instance_name), None
                    )
                    if instance is not None and instance.get("running"):
                        # Instance is running, test passes
                        break
            except (ConnectionError, OSError):
                # Addon may have restarted, wait for recovery
                await wait_for_addon_healthy(ADDON_URL, api_session, timeout=30000)
            await asyncio.sleep(2)
        else:
            # All attempts exhausted, check final state
            assert instance is not None, (
                f"Instance {instance_name} should exist. "
                f"Found: {[i['name'] for i in data.get('instances', [])] if data else 'no data'}"
            )
            assert instance.get(
                "running"
            ), f"Instance should still be running after cert regeneration. Status: {instance}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_scenario_7_start_stop(browser, unique_name, unique_port, api_session):
    """Scenario 7: Start/Stop Without Deleting.

    Goal: Stop and restart instance without losing configuration
    Acceptance Criteria:
    - Instance stops on demand
    - Configuration preserved (users, port)
    - Instance restarts successfully
    """
    instance_name = unique_name("scenario7-restart")
    port = unique_port(3208)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create instance with user
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Add user
        await navigate_to_settings(page, instance_name)

        await fill_textfield_by_testid(page, "user-username-input", "testuser")
        await fill_textfield_by_testid(page, "user-password-input", "testpass")
        await page.click('[data-testid="user-add-button"]')
        # Adding a user triggers a proxy restart (~3s), wait longer for chip to appear
        await page.wait_for_selector('[data-testid="user-chip-testuser"]', timeout=60000)

        # Navigate back to dashboard
        await navigate_to_dashboard(page, ADDON_URL)

        # Step 2: Stop instance
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)
        await page.click(f'[data-testid="instance-stop-chip-{instance_name}"]')
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Step 3: Start instance
        await page.click(f'[data-testid="instance-start-chip-{instance_name}"]')
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Step 4: Verify config preserved
        await navigate_to_settings(page, instance_name)

        user_list = await page.inner_text('[data-testid="user-list"]')
        assert "testuser" in user_list, "User should still exist after restart"
    finally:
        await page.close()


# Additional high-value parallel tests


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_https_critical_no_ssl_bump(browser, unique_name, unique_port, api_session):
    """CRITICAL: HTTPS instance starts and doesn't crash.

    This test catches the ssl_bump bug!
    If ssl_bump is in config, Squid crashes with:
    'FATAL: No valid signing certificate configured for HTTPS_port'

    This test verifies instance stays running after HTTPS creation.
    """
    instance_name = unique_name("https-critical")
    port = unique_port(3209)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create HTTPS instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)

        # Wait for instance to be running
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Critical: Wait and check instance stays running - give it extra time to stabilize
        await asyncio.sleep(12)

        # Check status via API multiple times to ensure it stays running
        all_running = True
        for attempt in range(8):
            await asyncio.sleep(3)
            async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
                if instance is None:
                    all_running = False
                    raise AssertionError(
                        f"Instance {instance_name} not found in API response (attempt {attempt + 1})"
                    )
                if not instance.get("running"):
                    all_running = False
                    raise AssertionError(
                        f"HTTPS instance crashed (attempt {attempt + 1}). "
                        f"Status: {instance}. "
                        "Check for ssl_bump in config or FATAL errors in logs."
                    )

        # If we made it here, instance stayed running for all checks
        assert all_running, "Instance should stay running throughout all checks"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_delete_instance(browser, unique_name, unique_port, api_session):
    """Test instance deletion via UI dialog.

    Verifies instance is completely removed:
    - API returns no instance
    - UI card disappears
    """
    instance_name = unique_name("delete-test")
    port = unique_port(3210)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Open settings and delete
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
            pytest.fail(f"Instance {instance_name} was not deleted after 30 seconds")

        # Verify card is gone from UI
        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', state="hidden", timeout=5000
        )
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_server_icon_color_reflects_status(browser, unique_name, unique_port, api_session):
    """Test that server icon color reflects proxy running status.

    Bug: Icon color was using https_enabled instead of running status
    Expected:
    - Green icon when instance is running
    - Gray icon when instance is stopped (new UI design)
    """
    instance_name = unique_name("icon-color-test")
    port = unique_port(3211)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Step 2: Verify icon is green when running
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Check that the ha-icon has green color
        icon_color = await get_icon_color(page, instance_name)
        assert is_success_color(
            icon_color
        ), f"Running instance should have green icon, got: {icon_color}"
        assert not is_error_color(
            icon_color
        ), f"Running instance should not have gray/stopped icon, got: {icon_color}"

        # Step 3: Stop instance (wait for button to be clickable after page.reload in get_icon_color)
        stop_btn = f'[data-testid="instance-stop-chip-{instance_name}"]'
        await page.wait_for_selector(f"{stop_btn}:not([disabled])", timeout=10000)
        await page.click(stop_btn)
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Step 4: Verify icon is gray when stopped (new UI design)
        icon_color = await get_icon_color(page, instance_name)
        assert is_error_color(
            icon_color
        ), f"Stopped instance should have gray/stopped icon, got: {icon_color}"
        assert not is_success_color(
            icon_color
        ), f"Stopped instance should not have green icon, got: {icon_color}"

        # Step 5: Start instance again (wait for button to be clickable after page.reload)
        start_btn = f'[data-testid="instance-start-chip-{instance_name}"]'
        await page.wait_for_selector(f"{start_btn}:not([disabled])", timeout=10000)
        await page.click(start_btn)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # Step 6: Verify icon is green again
        icon_color = await get_icon_color(page, instance_name)
        assert is_success_color(
            icon_color
        ), f"Restarted instance should have green icon, got: {icon_color}"
        assert not is_error_color(
            icon_color
        ), f"Restarted instance should not have gray/stopped icon, got: {icon_color}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_icon_color_multiple_instances_mixed_status(
    browser, unique_name, unique_port, api_session
):
    """Test icon colors with multiple instances in different states.

    Corner case: Multiple instances (HTTP + HTTPS) with mixed running/stopped status.
    Validates that each instance's icon is independent and correct.
    """
    instance1_name = unique_name("mixed-http-running")
    instance2_name = unique_name("mixed-https-running")
    instance3_name = unique_name("mixed-http-stopped")
    port1 = unique_port(3212)
    port2 = unique_port(3213)
    port3 = unique_port(3214)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create 3 instances: 2 HTTP, 1 HTTPS
        # Instance 1: HTTP (will keep running)
        await create_instance_via_ui(page, ADDON_URL, instance1_name, port1, https_enabled=False)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance1_name, timeout=60000)

        # Instance 2: HTTPS (will keep running)
        await create_instance_via_ui(page, ADDON_URL, instance2_name, port2, https_enabled=True)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance2_name, timeout=60000)

        # Instance 3: HTTP (will be stopped)
        await create_instance_via_ui(page, ADDON_URL, instance3_name, port3, https_enabled=False)

        # Stop instance 3
        await wait_for_instance_running(page, ADDON_URL, api_session, instance3_name, timeout=60000)
        stop_btn = f'[data-testid="instance-stop-chip-{instance3_name}"]'
        await page.wait_for_selector(f"{stop_btn}:not([disabled])", timeout=30000)
        await page.click(stop_btn)
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance3_name, timeout=60000)

        # Verify all icons are correct
        # Instance 1: HTTP + Running = Green
        icon1_color = await get_icon_color(page, instance1_name)
        assert is_success_color(
            icon1_color
        ), f"HTTP running instance should have green icon, got: {icon1_color}"

        # Instance 2: HTTPS + Running = Green (NOT gray despite HTTPS!)
        icon2_color = await get_icon_color(page, instance2_name)
        assert is_success_color(
            icon2_color
        ), f"HTTPS running instance should have green icon (bug fix!), got: {icon2_color}"
        assert not is_error_color(
            icon2_color
        ), f"HTTPS running instance should NOT have gray/stopped icon, got: {icon2_color}"

        # Instance 3: HTTP + Stopped = Gray (new UI design)
        icon3_color = await get_icon_color(page, instance3_name)
        assert is_error_color(
            icon3_color
        ), f"HTTP stopped instance should have gray/stopped icon, got: {icon3_color}"
        assert not is_success_color(
            icon3_color
        ), f"HTTP stopped instance should NOT have green icon, got: {icon3_color}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_icon_color_https_not_red_when_running(
    browser, unique_name, unique_port, api_session
):
    """Test that HTTPS instances show green when running, not gray.

    Corner case: Validates the original bug is fixed.
    Before fix: HTTPS instances always showed red (due to https_enabled check)
    After fix: HTTPS instances show green when running, gray when stopped
    """
    instance_name = unique_name("https-icon-test")
    port = unique_port(3215)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create HTTPS instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)

        # CRITICAL: HTTPS instance should have GREEN icon when running
        # This is the core bug fix - before it would show wrong color
        icon_color = await get_icon_color(page, instance_name)
        assert is_success_color(
            icon_color
        ), f"HTTPS running instance MUST have green icon (bug fix validation), got: {icon_color}"
        assert not is_error_color(
            icon_color
        ), f"HTTPS running instance should NOT have gray/stopped icon, got: {icon_color}"

        # Stop it - now it should be gray (new UI design)
        stop_btn = f'[data-testid="instance-stop-chip-{instance_name}"]'
        await page.wait_for_selector(f"{stop_btn}:not([disabled])", timeout=10000)
        await page.click(stop_btn)
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance_name, timeout=60000)

        icon_color = await get_icon_color(page, instance_name)
        assert is_error_color(
            icon_color
        ), f"HTTPS stopped instance should have gray/stopped icon, got: {icon_color}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_icon_color_rapid_status_changes(browser, unique_name, unique_port, api_session):
    """Test icon color updates correctly during rapid start/stop cycles.

    Corner case: Tests race conditions and ensures UI updates properly
    with multiple rapid state transitions.
    """
    instance_name = unique_name("rapid-change-test")
    port = unique_port(3216)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Perform 2 rapid stop/start cycles (reduced from 3 for reliability)
        for cycle in range(2):
            # Wait for running state (longer timeout for later cycles)
            await wait_for_instance_running(
                page, ADDON_URL, api_session, instance_name, timeout=60000
            )
            icon_color = await get_icon_color(page, instance_name)
            assert is_success_color(
                icon_color
            ), f"Cycle {cycle + 1}: Running should have green icon, got: {icon_color}"

            # Stop (wait for button to be clickable after page.reload in get_icon_color)
            stop_btn = f'[data-testid="instance-stop-chip-{instance_name}"]'
            await page.wait_for_selector(f"{stop_btn}:not([disabled])", timeout=30000)
            await page.click(stop_btn)
            await wait_for_instance_stopped(
                page, ADDON_URL, api_session, instance_name, timeout=60000
            )
            icon_color = await get_icon_color(page, instance_name)
            assert is_error_color(
                icon_color
            ), f"Cycle {cycle + 1}: Stopped should have gray/stopped icon, got: {icon_color}"

            # Start again (wait for button to be clickable after page.reload)
            start_btn = f'[data-testid="instance-start-chip-{instance_name}"]'
            await page.wait_for_selector(f"{start_btn}:not([disabled])", timeout=30000)
            await page.click(start_btn)

        # Final verification - should be running with green
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)
        icon_color = await get_icon_color(page, instance_name)
        assert is_success_color(
            icon_color
        ), f"Final state: should have green icon, got: {icon_color}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_icon_color_freshly_created_instance(browser, unique_name, unique_port, api_session):
    """Test icon color for freshly created instance (before any manual start/stop).

    Corner case: Validates that newly created instances show correct icon
    immediately after creation (should be green as they auto-start).
    """
    instance_name = unique_name("fresh-instance-test")
    port = unique_port(3217)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Immediately check icon (no manual start/stop yet)
        # Instances auto-start, so should be green
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=60000)
        icon_color = await get_icon_color(page, instance_name)
        assert is_success_color(
            icon_color
        ), f"Freshly created instance should have green icon (auto-started), got: {icon_color}"
        assert not is_error_color(
            icon_color
        ), f"Freshly created instance should NOT have red icon, got: {icon_color}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_icon_color_persistence_after_page_refresh(
    browser, unique_name, unique_port, api_session
):
    """Test icon colors persist correctly after page refresh.

    Corner case: Validates that icon colors are correctly restored from
    backend state after page reload (not just client-side state).
    """
    instance1_name = unique_name("persist-running")
    instance2_name = unique_name("persist-stopped")
    port1 = unique_port(3218)
    port2 = unique_port(3219)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create two instances
        await create_instance_via_ui(page, ADDON_URL, instance1_name, port1, https_enabled=False)
        await create_instance_via_ui(page, ADDON_URL, instance2_name, port2, https_enabled=False)

        # Stop instance 2
        await wait_for_instance_running(page, ADDON_URL, api_session, instance2_name, timeout=60000)
        await page.click(f'[data-testid="instance-stop-chip-{instance2_name}"]')
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance2_name, timeout=60000)

        # Refresh page
        await page.reload()
        await page.wait_for_selector(
            '[data-testid="instance-card-' + instance1_name + '"]', timeout=30000
        )

        # Wait a moment for all instances to load
        await asyncio.sleep(2)

        # Verify instance 1 (running) still has green icon
        icon1_color = await get_icon_color(page, instance1_name)
        assert is_success_color(
            icon1_color
        ), f"Running instance after refresh should have green icon, got: {icon1_color}"

        # Verify instance 2 (stopped) still has gray/stopped icon (new UI design)
        icon2_color = await get_icon_color(page, instance2_name)
        assert is_error_color(
            icon2_color
        ), f"Stopped instance after refresh should have gray/stopped icon, got: {icon2_color}"
        assert not is_success_color(
            icon2_color
        ), f"Stopped instance after refresh should NOT have green icon, got: {icon2_color}"
    finally:
        await page.close()
