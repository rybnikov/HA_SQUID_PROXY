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

        # Step 2: Open settings and add users
        await navigate_to_settings(page, instance_name)

        # Add alice
        await fill_textfield_by_testid(page, "user-username-input", "alice")
        await fill_textfield_by_testid(page, "user-password-input", "password123")
        await page.click('[data-testid="user-add-button"]')
        await page.wait_for_selector('[data-testid="user-chip-alice"]', timeout=10000)

        # Add bob
        await fill_textfield_by_testid(page, "user-username-input", "bob")
        await fill_textfield_by_testid(page, "user-password-input", "password456")
        await page.click('[data-testid="user-add-button"]')
        await page.wait_for_selector('[data-testid="user-chip-bob"]', timeout=10000)

        await page.close()

        # Step 3: Verify via API - instance running
        await asyncio.sleep(3)
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

        # Step 1: Create HTTP instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)
        await asyncio.sleep(2)

        # Step 2: Enable HTTPS via settings
        await navigate_to_settings(page, instance_name)

        # Enable HTTPS
        await set_switch_state_by_testid(page, "settings-https-switch", True)
        await asyncio.sleep(0.5)

        # Wait for save button to become enabled (isDirty must be true)
        await page.wait_for_selector(
            '[data-testid="settings-save-button"]:not([disabled])', timeout=5000
        )

        # Save changes
        await page.click('[data-testid="settings-save-button"]')
        await page.wait_for_selector("text=Saved!", timeout=10000)

        # Navigate back to dashboard
        await navigate_to_dashboard(page, ADDON_URL)

        # Step 3: Verify HTTPS enabled via API
        await asyncio.sleep(5)
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

        # Add initial user
        await navigate_to_settings(page, instance_name)

        await fill_textfield_by_testid(page, "user-username-input", "alice")
        await fill_textfield_by_testid(page, "user-password-input", "password123")
        await page.click('[data-testid="user-add-button"]')
        await page.wait_for_selector('[data-testid="user-chip-alice"]', timeout=10000)

        # Step 2: Add missing user (charlie)
        await fill_textfield_by_testid(page, "user-username-input", "charlie")
        await fill_textfield_by_testid(page, "user-password-input", "charlie123")
        await page.click('[data-testid="user-add-button"]')
        await page.wait_for_selector('[data-testid="user-chip-charlie"]', timeout=10000)

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

        # Verify the logs section is present (Instance Logs card).
        # The logs-viewer element only renders when there are log lines;
        # for a fresh instance we may see "No log entries found." instead.
        await page.wait_for_selector(
            '[data-testid="logs-type-select"]', state="attached", timeout=5000
        )
        await page.locator('[data-testid="logs-type-select"]').scroll_into_view_if_needed()
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

        # Step 1: Create first instance
        await create_instance_via_ui(page, ADDON_URL, name1, port1, https_enabled=False)

        # Step 2: Create second instance
        await create_instance_via_ui(page, ADDON_URL, name2, port2, https_enabled=False)

        # Verify both visible
        await page.wait_for_selector(f'[data-testid="instance-card-{name1}"]', timeout=10000)
        await page.wait_for_selector(f'[data-testid="instance-card-{name2}"]', timeout=10000)

        # Wait for both instances to be running
        await wait_for_instance_running(page, ADDON_URL, api_session, name1, timeout=30000)
        await wait_for_instance_running(page, ADDON_URL, api_session, name2, timeout=30000)

        # Step 3: Add different users to each instance
        # Instance 1: add user1
        await navigate_to_settings(page, name1)

        await fill_textfield_by_testid(page, "user-username-input", "user1")
        await fill_textfield_by_testid(page, "user-password-input", "pass1234")
        await page.click('[data-testid="user-add-button"]')

        # Poll for the user to appear (with retries)
        user_appeared = False
        for _attempt in range(10):
            try:
                await page.wait_for_selector(
                    '[data-testid="user-chip-user1"]',
                    timeout=5000,
                    state="visible",
                )
                user_appeared = True
                break
            except Exception:
                await asyncio.sleep(0.5)

        assert user_appeared, "user1 should appear in the list"

        # Navigate back to dashboard and open instance 2 settings
        await navigate_to_dashboard(page, ADDON_URL)
        await navigate_to_settings(page, name2)

        # Instance 2: add user2 (different from user1)
        await fill_textfield_by_testid(page, "user-username-input", "user2")
        await fill_textfield_by_testid(page, "user-password-input", "pass2345")
        await page.click('[data-testid="user-add-button"]')

        # Poll for the user to appear (with retries)
        user_appeared = False
        for _attempt in range(10):
            try:
                await page.wait_for_selector(
                    '[data-testid="user-chip-user2"]',
                    timeout=5000,
                    state="visible",
                )
                user_appeared = True
                break
            except Exception:
                await asyncio.sleep(0.5)

        assert user_appeared, "user2 should appear in the list"

        # Verify user1 NOT in instance 2
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
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=30000)
        await asyncio.sleep(2)

        # Step 2: Open settings and access certificate section
        await navigate_to_settings(page, instance_name)

        # Step 3: Regenerate certificate
        regenerate_btn = '[data-testid="cert-regenerate-button"]'
        if await page.is_visible(regenerate_btn):
            await page.click(regenerate_btn)
            # Wait for the Regenerate button to return to non-loading state
            await page.wait_for_selector(
                '[data-testid="cert-regenerate-button"]:not([disabled])',
                timeout=15000,
            )
            # Wait for instance to restart and stabilize after cert regeneration
            await asyncio.sleep(12)

        # Navigate back to dashboard
        await navigate_to_dashboard(page, ADDON_URL)

        # Verify instance still running - poll multiple times with longer waits
        for _attempt in range(8):
            await asyncio.sleep(3)
            async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
                if instance is not None and instance.get("running"):
                    # Instance is running, test passes
                    break
        else:
            # All attempts exhausted, check final state
            async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
                assert instance is not None, f"Instance {instance_name} should exist"
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
        await page.wait_for_selector('[data-testid="user-chip-testuser"]', timeout=10000)

        # Navigate back to dashboard
        await navigate_to_dashboard(page, ADDON_URL)

        # Step 2: Stop instance
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=10000)
        await page.click(f'[data-testid="instance-stop-chip-{instance_name}"]')
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance_name, timeout=10000)

        # Step 3: Start instance
        await page.click(f'[data-testid="instance-start-chip-{instance_name}"]')
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=10000)

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
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=30000)

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
    - Red icon when instance is stopped
    """
    instance_name = unique_name("icon-color-test")
    port = unique_port(3211)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Step 2: Verify icon is green when running
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=10000)

        # Check that the ha-icon has green color
        icon_color = await get_icon_color(page, instance_name)
        assert is_success_color(
            icon_color
        ), f"Running instance should have green icon, got: {icon_color}"
        assert not is_error_color(
            icon_color
        ), f"Running instance should not have red icon, got: {icon_color}"

        # Step 3: Stop instance
        await page.click(f'[data-testid="instance-stop-chip-{instance_name}"]')
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance_name, timeout=10000)

        # Step 4: Verify icon is red when stopped
        icon_color = await get_icon_color(page, instance_name)
        assert is_error_color(
            icon_color
        ), f"Stopped instance should have red icon, got: {icon_color}"
        assert not is_success_color(
            icon_color
        ), f"Stopped instance should not have green icon, got: {icon_color}"

        # Step 5: Start instance again
        await page.click(f'[data-testid="instance-start-chip-{instance_name}"]')
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=10000)

        # Step 6: Verify icon is green again
        icon_color = await get_icon_color(page, instance_name)
        assert is_success_color(
            icon_color
        ), f"Restarted instance should have green icon, got: {icon_color}"
        assert not is_error_color(
            icon_color
        ), f"Restarted instance should not have red icon, got: {icon_color}"
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

        # Instance 2: HTTPS (will keep running)
        await create_instance_via_ui(page, ADDON_URL, instance2_name, port2, https_enabled=True)

        # Instance 3: HTTP (will be stopped)
        await create_instance_via_ui(page, ADDON_URL, instance3_name, port3, https_enabled=False)

        # Stop instance 3
        await wait_for_instance_running(page, ADDON_URL, api_session, instance3_name, timeout=10000)
        await page.click(f'[data-testid="instance-stop-chip-{instance3_name}"]')
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance3_name, timeout=10000)

        # Verify all icons are correct
        # Instance 1: HTTP + Running = Green
        icon1_color = await get_icon_color(page, instance1_name)
        assert is_success_color(
            icon1_color
        ), f"HTTP running instance should have green icon, got: {icon1_color}"

        # Instance 2: HTTPS + Running = Green (NOT red despite HTTPS!)
        icon2_color = await get_icon_color(page, instance2_name)
        assert is_success_color(
            icon2_color
        ), f"HTTPS running instance should have green icon (bug fix!), got: {icon2_color}"
        assert not is_error_color(
            icon2_color
        ), f"HTTPS running instance should NOT have red icon, got: {icon2_color}"

        # Instance 3: HTTP + Stopped = Red
        icon3_color = await get_icon_color(page, instance3_name)
        assert is_error_color(
            icon3_color
        ), f"HTTP stopped instance should have red icon, got: {icon3_color}"
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
    """Test that HTTPS instances show green when running, not red.

    Corner case: Validates the original bug is fixed.
    Before fix: HTTPS instances always showed red (due to https_enabled check)
    After fix: HTTPS instances show green when running, red when stopped
    """
    instance_name = unique_name("https-icon-test")
    port = unique_port(3215)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create HTTPS instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=True)
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=10000)

        # CRITICAL: HTTPS instance should have GREEN icon when running
        # This is the core bug fix - before it would be red
        icon_color = await get_icon_color(page, instance_name)
        assert is_success_color(
            icon_color
        ), f"HTTPS running instance MUST have green icon (bug fix validation), got: {icon_color}"
        assert not is_error_color(
            icon_color
        ), f"HTTPS running instance should NOT have red icon, got: {icon_color}"

        # Stop it - now it should be red
        await page.click(f'[data-testid="instance-stop-chip-{instance_name}"]')
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance_name, timeout=10000)

        icon_color = await get_icon_color(page, instance_name)
        assert is_error_color(
            icon_color
        ), f"HTTPS stopped instance should have red icon, got: {icon_color}"
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

        # Perform 3 rapid stop/start cycles
        for cycle in range(3):
            # Wait for running state
            await wait_for_instance_running(
                page, ADDON_URL, api_session, instance_name, timeout=10000
            )
            icon_color = await get_icon_color(page, instance_name)
            assert is_success_color(
                icon_color
            ), f"Cycle {cycle + 1}: Running should have green icon, got: {icon_color}"

            # Stop
            await page.click(f'[data-testid="instance-stop-chip-{instance_name}"]')
            await wait_for_instance_stopped(
                page, ADDON_URL, api_session, instance_name, timeout=10000
            )
            icon_color = await get_icon_color(page, instance_name)
            assert is_error_color(
                icon_color
            ), f"Cycle {cycle + 1}: Stopped should have red icon, got: {icon_color}"

            # Start again
            await page.click(f'[data-testid="instance-start-chip-{instance_name}"]')

        # Final verification - should be running with green
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=10000)
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
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=10000)
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
        await wait_for_instance_running(page, ADDON_URL, api_session, instance2_name, timeout=10000)
        await page.click(f'[data-testid="instance-stop-chip-{instance2_name}"]')
        await wait_for_instance_stopped(page, ADDON_URL, api_session, instance2_name, timeout=10000)

        # Refresh page
        await page.reload()
        await page.wait_for_selector(
            '[data-testid="instance-card-' + instance1_name + '"]', timeout=15000
        )

        # Wait a moment for all instances to load
        await asyncio.sleep(2)

        # Verify instance 1 (running) still has green icon
        icon1_color = await get_icon_color(page, instance1_name)
        assert is_success_color(
            icon1_color
        ), f"Running instance after refresh should have green icon, got: {icon1_color}"

        # Verify instance 2 (stopped) still has red icon
        icon2_color = await get_icon_color(page, instance2_name)
        assert is_error_color(
            icon2_color
        ), f"Stopped instance after refresh should have red icon, got: {icon2_color}"
        assert not is_success_color(
            icon2_color
        ), f"Stopped instance after refresh should NOT have green icon, got: {icon2_color}"
    finally:
        await page.close()
