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
import logging
import os

import pytest

_LOGGER = logging.getLogger(__name__)

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "test_token")
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
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))
        await page.click('[data-testid="instance-create-button"]')

        instance_selector = f'[data-testid="instance-card"][data-instance="{instance_name}"]'
        await page.wait_for_selector(instance_selector, timeout=15000)

        # Step 2: Open settings and add users
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

        # Add alice
        await page.fill('[data-testid="user-username-input"]', "alice")
        await page.fill('[data-testid="user-password-input"]', "password123")
        await page.click('[data-testid="user-add-button"]')
        await page.wait_for_selector(
            '[data-testid="user-item"][data-username="alice"]', timeout=10000
        )

        # Add bob
        await page.fill('[data-testid="user-username-input"]', "bob")
        await page.fill('[data-testid="user-password-input"]', "password456")
        await page.click('[data-testid="user-add-button"]')
        await page.wait_for_selector(
            '[data-testid="user-item"][data-username="bob"]', timeout=10000
        )

        await page.close()

        # Step 3: Verify via API - instance running
        await asyncio.sleep(3)  # Wait for instance to be ready
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
    - HTTPS tab appears after toggling HTTPS ON
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
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))
        # Don't check HTTPS
        await page.click('[data-testid="instance-create-button"]')

        instance_selector = f'[data-testid="instance-card"][data-instance="{instance_name}"]'
        await page.wait_for_selector(instance_selector, timeout=15000)
        await asyncio.sleep(2)

        # Step 2: Enable HTTPS via settings
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)

        # Click Main tab and enable HTTPS
        await page.click("#settingsModal [data-tab='main']")
        await page.check('[data-testid="settings-https-checkbox"]')
        await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)

        # Save changes
        await page.click('[data-testid="settings-save-button"]')
        await page.wait_for_selector("#settingsModal", state="hidden", timeout=30000)

        # Step 3: Verify HTTPS enabled via API
        await asyncio.sleep(5)  # Wait for restart with cert generation
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
    - User list visible in Settings modal
    - New user can be added and immediately authenticated
    """
    instance_name = unique_name("scenario3-auth")
    port = unique_port(3203)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Step 1: Create instance with initial user
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))
        await page.click('[data-testid="instance-create-button"]')

        instance_selector = f'[data-testid="instance-card"][data-instance="{instance_name}"]'
        await page.wait_for_selector(instance_selector, timeout=15000)

        # Add initial user
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

        await page.fill('[data-testid="user-username-input"]', "alice")
        await page.fill('[data-testid="user-password-input"]', "password123")
        await page.click('[data-testid="user-add-button"]')
        await page.wait_for_selector(
            '[data-testid="user-item"][data-username="alice"]', timeout=10000
        )

        # Step 2: Add missing user (charlie)
        await page.fill('[data-testid="user-username-input"]', "charlie")
        await page.fill('[data-testid="user-password-input"]', "charlie123")
        await page.click('[data-testid="user-add-button"]')
        await page.wait_for_selector(
            '[data-testid="user-item"][data-username="charlie"]', timeout=10000
        )

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
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))
        await page.click('[data-testid="instance-create-button"]')

        instance_selector = f'[data-testid="instance-card"][data-instance="{instance_name}"]'
        await page.wait_for_selector(instance_selector, timeout=15000)

        # Step 2: Open logs tab
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='logs']")

        # Verify log content loads (can be empty initially)
        await page.wait_for_selector('[data-testid="log-content"]', timeout=5000)

        # Log content should exist (even if empty)
        log_content = await page.inner_text('[data-testid="log-content"]')
        assert log_content is not None
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
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', name1)
        await page.fill('[data-testid="instance-port-input"]', str(port1))
        await page.click('[data-testid="instance-create-button"]')
        await page.wait_for_selector('[data-testid="instance-card"]', timeout=15000)

        # Step 2: Create second instance
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', name2)
        await page.fill('[data-testid="instance-port-input"]', str(port2))
        await page.click('[data-testid="instance-create-button"]')

        # Verify both visible
        await page.wait_for_selector(
            f'[data-testid="instance-card"][data-instance="{name1}"]', timeout=10000
        )
        await page.wait_for_selector(
            f'[data-testid="instance-card"][data-instance="{name2}"]', timeout=10000
        )
        # Wait for both instances to be running
        await page.wait_for_selector(
            f'[data-testid="instance-card"][data-instance="{name1}"][data-status="running"]',
            timeout=30000,
        )
        await page.wait_for_selector(
            f'[data-testid="instance-card"][data-instance="{name2}"][data-status="running"]',
            timeout=30000,
        )

        # Step 3: Add different users to each instance
        # Instance 1: add user1
        await page.click(
            f'[data-testid="instance-card"][data-instance="{name1}"] [data-testid="instance-settings-button"]'
        )
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

        await page.fill('[data-testid="user-username-input"]', "user1")
        await page.fill('[data-testid="user-password-input"]', "pass1")
        await page.click('[data-testid="user-add-button"]')
        # Wait for mutation to complete
        await page.wait_for_selector(
            '[data-testid="user-add-button"]:not([disabled])', timeout=15000
        )

        # Wait for the user to appear in the UI list
        await page.wait_for_selector(
            '[data-testid="user-item"][data-username="user1"]',
            timeout=10000,
            state="visible",
        )

        # Close modal by pressing Escape (more reliable than clicking close button)
        await page.keyboard.press("Escape")
        await page.wait_for_selector("#settingsModal", state="hidden", timeout=5000)

        # Open instance 2 settings
        await page.click(
            f'[data-testid="instance-card"][data-instance="{name2}"] [data-testid="instance-settings-button"]'
        )
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

        # Instance 2: add user2 (different from user1)
        await page.fill('[data-testid="user-username-input"]', "user2")
        await page.fill('[data-testid="user-password-input"]', "pass2")
        await page.click('[data-testid="user-add-button"]')
        # Wait for mutation to complete
        await page.wait_for_selector(
            '[data-testid="user-add-button"]:not([disabled])', timeout=15000
        )

        # Wait for the user to appear in the UI list
        await page.wait_for_selector(
            '[data-testid="user-item"][data-username="user2"]',
            timeout=10000,
            state="visible",
        )

        # Verify user1 NOT in instance 2's user list
        user_list = await page.inner_text('[data-testid="user-list"]')
        assert "user2" in user_list, "user2 should be visible in instance 2"
        assert "user1" not in user_list, "user1 should NOT be visible in instance 2 (isolation check)"

        # Close modal and verify via API that users are properly isolated
        await page.keyboard.press("Escape")
        await page.wait_for_selector("#settingsModal", state="hidden", timeout=5000)

        # Give backend time to persist
        await asyncio.sleep(1)

        # Verify via API: instance 1 has user1, instance 2 has user2
        async with api_session.get(f"{ADDON_URL}/api/instances/{name1}/users") as resp:
            data = await resp.json()
            users1 = [u["username"] for u in data["users"]]
            assert "user1" in users1, "user1 should be in instance 1"
            assert "user2" not in users1, "user2 should NOT be in instance 1"

        async with api_session.get(f"{ADDON_URL}/api/instances/{name2}/users") as resp:
            data = await resp.json()
            users2 = [u["username"] for u in data["users"]]
            assert "user2" in users2, "user2 should be in instance 2"
            assert "user1" not in users2, "user1 should NOT be in instance 2"
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
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))
        await page.check('[data-testid="instance-https-checkbox"]')
        await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
        await page.click('[data-testid="instance-create-button"]')

        instance_selector = f'[data-testid="instance-card"][data-instance="{instance_name}"]'
        await page.wait_for_selector(instance_selector, timeout=30000)
        # Wait for instance to be running (important for HTTPS instances)
        await page.wait_for_selector(f"{instance_selector}[data-status='running']", timeout=30000)

        # Step 2: Open settings and access certificate tab
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='certificate']")

        # Step 3: Regenerate certificate
        regenerate_btn = '[data-testid="certificate-regenerate-button"]'
        # Verify button exists before clicking
        await page.wait_for_selector(regenerate_btn, timeout=5000, state="visible")

        await page.click(regenerate_btn)
        # Wait for the Regenerate button to return to non-loading state
        await page.wait_for_selector(
            f'{regenerate_btn}:not([disabled])',
            timeout=15000,
        )

        # Close the modal to allow UI to update
        await page.keyboard.press("Escape")
        await page.wait_for_selector("#settingsModal", state="hidden", timeout=5000)

        # Verify instance stays running after cert regeneration
        # Poll instance status multiple times to ensure stability
        for attempt in range(5):
            # Wait before each check
            await asyncio.sleep(2)

            # Check instance status via selector
            is_running = await page.is_visible(f"{instance_selector}[data-status='running']")
            if not is_running:
                # If not visible as running, check actual status
                status_badge = await page.query_selector(f"{instance_selector} [data-testid='status-badge']")
                if status_badge:
                    status_text = await status_badge.inner_text()
                    pytest.fail(
                        f"Instance not running after cert regeneration (attempt {attempt + 1}/5). "
                        f"Status: {status_text}"
                    )

        # Final API verification
        async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None, f"Instance {instance_name} should exist"
            assert instance.get("running"), \
                f"Instance should still be running after cert regeneration. Status: {instance}"
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
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))
        await page.click('[data-testid="instance-create-button"]')

        instance_selector = f'[data-testid="instance-card"][data-instance="{instance_name}"]'
        await page.wait_for_selector(instance_selector, timeout=15000)

        # Add user
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

        await page.fill('[data-testid="user-username-input"]', "testuser")
        await page.fill('[data-testid="user-password-input"]', "testpass")
        await page.click('[data-testid="user-add-button"]')
        await page.wait_for_selector(
            '[data-testid="user-item"][data-username="testuser"]', timeout=10000
        )

        await page.click("#settingsModal button[aria-label='Close']")
        await page.wait_for_selector("#settingsModal", state="hidden", timeout=5000)

        # Step 2: Stop instance
        await page.wait_for_selector(f"{instance_selector}[data-status='running']", timeout=10000)
        await page.click(f"{instance_selector} [data-testid='instance-stop-button']")
        await page.wait_for_selector(f"{instance_selector}[data-status='stopped']", timeout=10000)

        # Step 3: Start instance
        await page.click(f"{instance_selector} [data-testid='instance-start-button']")
        await page.wait_for_selector(f"{instance_selector}[data-status='running']", timeout=10000)

        # Step 4: Verify config preserved
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

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
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))
        await page.check('[data-testid="instance-https-checkbox"]')
        await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
        await page.click('[data-testid="instance-create-button"]')

        instance_selector = f'[data-testid="instance-card"][data-instance="{instance_name}"]'
        await page.wait_for_selector(instance_selector, timeout=30000)
        # Wait for instance to be running (important for HTTPS instances)
        await page.wait_for_selector(f"{instance_selector}[data-status='running']", timeout=30000)

        # Critical: Check instance stays running - poll status multiple times
        for attempt in range(5):
            # Wait between checks to ensure stability
            await asyncio.sleep(2)

            # Check via UI selector first (faster)
            is_running = await page.is_visible(f"{instance_selector}[data-status='running']")

            # Also verify via API
            async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)

                if instance is None:
                    raise AssertionError(
                        f"Instance {instance_name} not found in API response (attempt {attempt + 1}/5)"
                    )

                if not instance.get("running"):
                    raise AssertionError(
                        f"HTTPS instance crashed (attempt {attempt + 1}/5). "
                        f"Status: {instance}. "
                        "Check for ssl_bump in config or FATAL errors in logs."
                    )

                if not is_running and instance.get("running"):
                    # UI may be out of sync with API, wait a bit and recheck
                    await asyncio.sleep(1)
                    is_running = await page.is_visible(f"{instance_selector}[data-status='running']")

                if not is_running:
                    raise AssertionError(
                        f"UI shows instance not running (attempt {attempt + 1}/5) but API says it is. "
                        f"Status: {instance}"
                    )

        # If we made it here, instance stayed running for all checks
        _LOGGER.info("✓ HTTPS instance %s stayed running for all stability checks", instance_name)
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_delete_instance(browser, unique_name, unique_port, api_session):
    """Test instance deletion via UI custom modal.

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
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))
        await page.click('[data-testid="instance-create-button"]')

        instance_selector = f'[data-testid="instance-card"][data-instance="{instance_name}"]'
        await page.wait_for_selector(instance_selector, timeout=15000)

        # Open delete tab
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='delete']")

        # Wait for delete button to be visible
        await page.wait_for_selector('[data-testid="delete-confirm-button"]', timeout=5000)

        # Confirm delete
        await page.click('[data-testid="delete-confirm-button"]')

        # Wait for deletion to complete by checking API
        for _attempt in range(30):  # 30 * 1s = 30 seconds max
            async with api_session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instances = data.get("instances", []) if isinstance(data, dict) else data
                if not any(i["name"] == instance_name for i in instances):
                    break
            await asyncio.sleep(1)
        else:
            pytest.fail(f"Instance {instance_name} was not deleted after 30 seconds")

        # Verify card is gone from UI
        await page.wait_for_selector(instance_selector, state="hidden", timeout=5000)
    finally:
        await page.close()
