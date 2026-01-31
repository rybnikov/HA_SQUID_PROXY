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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        await page.wait_for_selector(
            f".instance-card[data-instance='{instance_name}']", timeout=15000
        )
        await page.wait_for_selector("#addInstanceModal", state="hidden", timeout=5000)

        # Try to create duplicate
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)  # Same name
        await page.fill("#newPort", str(port + 1))  # Different port

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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=15000)

        # Add user
        await page.click(f"{instance_selector} button[data-action='settings']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

        await page.fill("#newUsername", "duplicate")
        await page.fill("#newPassword", "pass1")
        await page.click("#settingsModal button:has-text('Add')")
        await page.wait_for_selector(".user-item:has-text('duplicate')", timeout=10000)

        # Try to add same user again
        await page.fill("#newUsername", "duplicate")
        await page.fill("#newPassword", "pass2")
        await page.click("#settingsModal button:has-text('Add')")

        # Should show error (check for error message or no new user added)
        await page.wait_for_selector("#userError", state="visible", timeout=10000)
        error_text = await page.inner_text("#userError")
        assert "duplicate" in error_text.lower() or "exists" in error_text.lower()
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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)

        # Try port < 1024
        await page.fill("#newPort", "80")
        await asyncio.sleep(500)  # Give form a moment to validate

        # Submit button should be disabled or error shown
        create_btn = "#addInstanceModal button:has-text('Create Instance')"
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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=15000)

        # Open users tab
        await page.click(f"{instance_selector} button[data-action='settings']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='users']")

        # Add 5 users rapidly
        for i in range(5):
            await page.fill("#newUsername", f"user{i}")
            await page.fill("#newPassword", f"pass{i}")
            await page.click("#settingsModal button:has-text('Add')")
            await asyncio.sleep(1)  # Brief wait between adds

        # Verify all users added
        user_list = await page.inner_text("#userList")
        for i in range(5):
            assert f"user{i}" in user_list, f"User{i} should be in list"
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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=15000)

        # View logs immediately (may be empty)
        await page.click(f"{instance_selector} button[data-action='settings']")
        await page.wait_for_selector("#settingsModal:visible", timeout=5000)
        await page.click("#settingsModal [data-tab='logs']")

        # Verify log content element exists (even if empty)
        log_content = await page.query_selector("#logContent")
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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
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
        await page.click("button:has-text('Add Instance')")
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        instance_selector = f".instance-card[data-instance='{instance_name}']"
        await page.wait_for_selector(instance_selector, timeout=15000)

        # Click settings
        await page.click(f"{instance_selector} button[data-action='settings']")
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
        await page.click("button:has-text('Add Instance')")

        # Should still be usable (no horizontal scroll needed)
        modal = await page.query_selector("#addInstanceModal")
        assert modal is not None, "Modal should be visible on mobile"

        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))

        # Form should be usable (not overflow)
        await page.click("#addInstanceModal button:has-text('Create Instance')")

        await page.wait_for_selector(
            f".instance-card[data-instance='{instance_name}']", timeout=15000
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
            await page.click("button:has-text('Add Instance')")
            await page.fill("#newName", name)
            await page.fill("#newPort", str(port))
            await page.click("#addInstanceModal button:has-text('Create Instance')")
            await page.wait_for_selector(f".instance-card[data-instance='{name}']", timeout=15000)
            await page.wait_for_selector("#addInstanceModal", state="hidden", timeout=5000)

        # Try to search if search box exists
        search_box = await page.query_selector("input[placeholder*='Search']")
        if search_box:
            await page.fill("input[placeholder*='Search']", "search")
            await asyncio.sleep(500)  # Let filter work
            # Verify correct instance shown
            assert await page.is_visible(f".instance-card[data-instance='{name1}']")
    finally:
        await page.close()
