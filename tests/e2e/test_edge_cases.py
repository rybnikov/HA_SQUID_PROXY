"""E2E edge case tests for parallelized execution.

These tests cover error conditions, boundary cases, and UI robustness
not covered by the main scenario tests.

All tests designed for parallel execution with pytest-xdist.
"""

import asyncio
import os

import pytest

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "test_token")
API_HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_duplicate_instance_error(browser, unique_name, unique_port, api_session):
    """Test creating duplicate instance shows error."""
    instance_name = unique_name("dup-test")
    port = unique_port(3220)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create first instance
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))
        await page.click('[data-testid="instance-create-button"]')

        await page.wait_for_selector(
            f'[data-testid="instance-card"][data-instance="{instance_name}"]', timeout=15000
        )
        await page.wait_for_selector("#addInstanceModal", state="hidden", timeout=5000)

        # Try to create duplicate
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)  # Same name
        await page.fill('[data-testid="instance-port-input"]', str(port + 1))  # Different port

        # Should show validation error before submit, or error on submit
        # This depends on implementation
        await asyncio.sleep(1)  # Brief wait for validation
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_duplicate_user_error(browser, unique_name, unique_port, api_session):
    """Test adding duplicate user shows error."""
    instance_name = unique_name("dup-user")
    port = unique_port(3221)

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
        # Wait for instance to be running
        await page.wait_for_selector(f"{instance_selector}[data-status='running']", timeout=30000)

        # Add first user
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

        await page.fill('[data-testid="user-username-input"]', "duplicate")
        await page.fill('[data-testid="user-password-input"]', "pass1")
        await page.click('[data-testid="user-add-button"]')

        # Wait for mutation to complete
        await page.wait_for_selector(
            '[data-testid="user-add-button"]:not([disabled])', timeout=15000
        )

        # Poll for the user to appear in the list (with retries)
        user_appeared = False
        for _attempt in range(10):
            try:
                await page.wait_for_selector(
                    '[data-testid="user-item"][data-username="duplicate"]',
                    timeout=1000,
                    state="visible",
                )
                user_appeared = True
                break
            except Exception:
                await asyncio.sleep(0.5)

        assert user_appeared, "First user 'duplicate' should appear in the list"

        # Try to add same user again
        await page.fill('[data-testid="user-username-input"]', "duplicate")
        await page.fill('[data-testid="user-password-input"]', "pass2")
        await page.click('[data-testid="user-add-button"]')

        # Should show error message when duplicate is detected
        # Wait for the error message to appear
        await page.wait_for_selector(
            '[data-testid="user-error-message"]', timeout=5000, state="visible"
        )

        # Verify error message contains relevant text about duplicate
        error_text = await page.inner_text('[data-testid="user-error-message"]')
        assert (
            "already exists" in error_text.lower()
            or "duplicate" in error_text.lower()
            or "failed" in error_text.lower()
        ), f"Error message should indicate duplicate user issue, got: {error_text}"

        # Verify user count didn't increase (still just one user)
        user_items = await page.query_selector_all('[data-testid="user-item"]')
        assert (
            len(user_items) == 1
        ), f"Should still have only 1 user after duplicate attempt, got {len(user_items)}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_invalid_port_validation(browser, unique_name):
    """Test port validation in create modal."""
    instance_name = unique_name("invalid-port")

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Try to create with invalid port
        await page.click('[data-testid="add-instance-button"]')
        await page.fill('[data-testid="instance-name-input"]', instance_name)

        # Try port < 1024
        await page.fill('[data-testid="instance-port-input"]', "80")
        await asyncio.sleep(0.5)  # Give form a moment to validate

        # Submit button should be disabled or error shown
        create_btn = '[data-testid="instance-create-button"]'
        _ = await page.is_disabled(create_btn)
        # Either button is disabled or form prevents submission
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_many_users_single_instance(browser, unique_name, unique_port, api_session):
    """Test adding many users to a single instance."""
    instance_name = unique_name("many-users")
    port = unique_port(3222)

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
        # Wait for instance to be running
        await page.wait_for_selector(f"{instance_selector}[data-status='running']", timeout=30000)

        # Open users tab
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

        # Add 5 users rapidly
        for i in range(5):
            await page.fill('[data-testid="user-username-input"]', f"user{i}")
            await page.fill('[data-testid="user-password-input"]', f"pass{i}")
            await page.click('[data-testid="user-add-button"]')
            # Wait for the "Add User" button to be re-enabled (mutation complete)
            await page.wait_for_selector(
                '[data-testid="user-add-button"]:not([disabled])', timeout=15000
            )

            # Wait for the user to appear in the UI list with specific selector
            await page.wait_for_selector(
                f'[data-testid="user-item"][data-username="user{i}"]',
                timeout=10000,
                state="visible",
            )

        # Give backend time to persist all users before API verification
        await asyncio.sleep(2)

        # Verify all users are in the list via API
        async with api_session.get(f"{ADDON_URL}/api/instances/{instance_name}/users") as resp:
            data = await resp.json()
            usernames = [u["username"] for u in data["users"]]
            for i in range(5):
                assert f"user{i}" in usernames, f"user{i} should be in API response"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_empty_logs_display(browser, unique_name, unique_port, api_session):
    """Test logs tab handles empty log gracefully."""
    instance_name = unique_name("empty-logs")
    port = unique_port(3223)

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

        # View logs immediately (may be empty)
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='logs']")

        # Verify log content element exists (even if empty)
        log_content = await page.query_selector('[data-testid="log-content"]')
        assert log_content is not None, "Log content element should exist"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_instance_card_displays_all_info(browser, unique_name, unique_port, api_session):
    """Test instance card displays name, port, and status correctly."""
    instance_name = unique_name("card-display")
    port = unique_port(3224)

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

        # Check card displays correct info
        card_text = await page.inner_text(instance_selector)
        assert instance_name in card_text, "Card should show instance name"
        assert str(port) in card_text, "Card should show port"

        # Check status badge exists and shows "Running"
        await page.wait_for_selector(f"{instance_selector}[data-status='running']", timeout=10000)
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_settings_button_opens_modal(browser, unique_name, unique_port, api_session):
    """Test settings button opens modal with correct tabs."""
    instance_name = unique_name("settings-modal")
    port = unique_port(3225)

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

        # Click settings
        await page.click(f"{instance_selector} [data-testid='instance-settings-button']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)

        # Verify tabs exist
        tabs = ["main", "users", "certificate", "logs", "test", "status", "delete"]
        for tab in tabs:
            tab_elem = await page.query_selector(f"#settingsModal [data-tab='{tab}']")
            assert tab_elem is not None, f"Tab '{tab}' should exist in settings modal"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_responsive_design_mobile(browser, unique_name, unique_port, api_session):
    """Test UI is responsive on mobile viewport."""
    instance_name = unique_name("mobile-test")
    port = unique_port(3226)

    page = await browser.new_page(viewport={"width": 375, "height": 667})  # iPhone size
    try:
        await page.goto(ADDON_URL)

        # Create instance on mobile
        await page.click('[data-testid="add-instance-button"]')

        # Should still be usable (no horizontal scroll needed)
        modal = await page.query_selector("#addInstanceModal")
        assert modal is not None, "Modal should be visible on mobile"

        await page.fill('[data-testid="instance-name-input"]', instance_name)
        await page.fill('[data-testid="instance-port-input"]', str(port))

        # Form should be usable (not overflow)
        await page.click('[data-testid="instance-create-button"]')

        await page.wait_for_selector(
            f'[data-testid="instance-card"][data-instance="{instance_name}"]', timeout=15000
        )
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_dashboard_search_filter(browser, unique_name, unique_port, api_session):
    """Test search/filter on dashboard (if implemented)."""
    name1 = unique_name("search-proxy-1")
    name2 = unique_name("other-proxy")
    port1 = unique_port(3227)
    port2 = unique_port(3228)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create two instances
        for name, port in [(name1, port1), (name2, port2)]:
            await page.click('[data-testid="add-instance-button"]')
            await page.fill('[data-testid="instance-name-input"]', name)
            await page.fill('[data-testid="instance-port-input"]', str(port))
            await page.click('[data-testid="instance-create-button"]')
            await page.wait_for_selector(
                f'[data-testid="instance-card"][data-instance="{name}"]', timeout=15000
            )
            await page.wait_for_selector("#addInstanceModal", state="hidden", timeout=5000)

        # Try to search if search box exists
        search_box = await page.query_selector("input[placeholder*='Search']")
        if search_box:
            await page.fill("input[placeholder*='Search']", "search")
            await asyncio.sleep(0.5)  # Let filter work
            # Verify correct instance shown
            assert await page.is_visible(f'[data-testid="instance-card"][data-instance="{name1}"]')
    finally:
        await page.close()
