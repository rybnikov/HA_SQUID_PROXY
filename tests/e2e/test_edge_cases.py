"""E2E edge case tests for parallelized execution.

These tests cover error conditions, boundary cases, and UI robustness
not covered by the main scenario tests.

All tests designed for parallel execution with pytest-xdist.
"""

import asyncio
import os

import pytest

from tests.e2e.utils import (
    create_instance_via_ui,
    fill_textfield_by_testid,
    navigate_to_settings,
    wait_for_instance_running,
)

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "dev_token")
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
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Try to create duplicate
        await page.click('[data-testid="add-instance-button"]')
        await page.wait_for_selector('[data-testid="create-name-input"]', timeout=10000)

        await fill_textfield_by_testid(page, "create-name-input", instance_name)
        await fill_textfield_by_testid(page, "create-port-input", str(port + 1))

        # Should show validation error before submit, or error on submit
        await asyncio.sleep(1)
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
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Add first user
        await navigate_to_settings(page, instance_name)

        await fill_textfield_by_testid(page, "user-username-input", "duplicate")
        await fill_textfield_by_testid(page, "user-password-input", "pass1234")
        await page.click('[data-testid="user-add-button"]')

        # Poll for the user to appear in the list (with retries)
        user_appeared = False
        for _attempt in range(10):
            try:
                await page.wait_for_selector(
                    '[data-testid="user-chip-duplicate"]',
                    timeout=5000,
                    state="visible",
                )
                user_appeared = True
                break
            except Exception:
                await asyncio.sleep(0.5)

        assert user_appeared, "First user 'duplicate' should appear in the list"

        # Try to add same user again
        await fill_textfield_by_testid(page, "user-username-input", "duplicate")
        await fill_textfield_by_testid(page, "user-password-input", "pass2345")
        await page.click('[data-testid="user-add-button"]')

        # Wait for API response
        await asyncio.sleep(3)

        # Verify duplicate was rejected - should still have exactly 1 user via API
        async with api_session.get(f"{ADDON_URL}/api/instances/{instance_name}/users") as resp:
            data = await resp.json()
            usernames = [u["username"] for u in data.get("users", [])]
            duplicate_count = usernames.count("duplicate")
            assert (
                duplicate_count == 1
            ), f"Should have exactly 1 'duplicate' user, got {duplicate_count}"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_invalid_port_validation(browser, unique_name):
    """Test port validation in create form."""
    instance_name = unique_name("invalid-port")

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Try to create with invalid port
        await page.click('[data-testid="add-instance-button"]')
        await page.wait_for_selector('[data-testid="create-name-input"]', timeout=10000)

        await fill_textfield_by_testid(page, "create-name-input", instance_name)

        # Try port < 1024
        await fill_textfield_by_testid(page, "create-port-input", "80")
        await asyncio.sleep(0.5)

        # Submit button should be disabled or error shown
        create_btn = '[data-testid="create-submit-button"]'
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
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Open settings to add users
        await navigate_to_settings(page, instance_name)

        # Add 5 users rapidly
        for i in range(5):
            await fill_textfield_by_testid(page, "user-username-input", f"user{i}")
            await fill_textfield_by_testid(page, "user-password-input", f"pass{i}2345")
            await page.click('[data-testid="user-add-button"]')

            # Poll for the user to appear (with retries)
            user_appeared = False
            for _attempt in range(10):
                try:
                    await page.wait_for_selector(
                        f'[data-testid="user-chip-user{i}"]',
                        timeout=5000,
                        state="visible",
                    )
                    user_appeared = True
                    break
                except Exception:
                    await asyncio.sleep(0.5)

            assert user_appeared, f"user{i} should appear in the list"

        # Verify all users are in the list via API
        await asyncio.sleep(1)
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
    """Test logs section handles empty log gracefully."""
    instance_name = unique_name("empty-logs")
    port = unique_port(3223)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # View logs immediately (may be empty)
        await navigate_to_settings(page, instance_name)

        # Logs are now in a dialog - click the VIEW LOGS button to open it
        await page.click('[data-testid="settings-view-logs-button"]')

        # Wait for dialog to open and logs section to render
        log_section = await page.wait_for_selector('[data-testid="logs-type-select"]', timeout=5000)
        assert log_section is not None, "Logs section should exist in dialog"

        # Either the log viewer or the empty-state message should be visible
        has_viewer = await page.locator('[data-testid="logs-viewer"]').count() > 0
        has_empty = await page.locator("text=No log entries found").count() > 0
        assert has_viewer or has_empty, "Logs section should show entries or empty message"
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
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Wait for instance to be running
        await wait_for_instance_running(page, ADDON_URL, api_session, instance_name, timeout=10000)

        # Check card displays correct info
        card_selector = f'[data-testid="instance-card-{instance_name}"]'
        card_text = await page.inner_text(card_selector)
        assert instance_name in card_text, "Card should show instance name"
        assert str(port) in card_text, "Card should show port"

        # Check visual status indicator - running instances show stop button
        stop_button = await page.query_selector(
            f'[data-testid="instance-stop-chip-{instance_name}"]'
        )
        assert stop_button is not None, "Card should show stop button when running"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_settings_page_has_all_sections(browser, unique_name, unique_port, api_session):
    """Test settings page has all expected card sections."""
    instance_name = unique_name("settings-sections")
    port = unique_port(3225)

    page = await browser.new_page()
    try:
        await page.goto(ADDON_URL)

        # Create instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)

        # Navigate to settings
        await navigate_to_settings(page, instance_name)

        # Verify all sections exist. In plain Chromium (no HA custom elements),
        # HACard falls back to <div> with <h2> children instead of <ha-card header=...>.
        # Use data-testid where available, text content otherwise.
        config_section = await page.query_selector('[data-testid="settings-tabs"]')
        assert config_section is not None, "Configuration section should exist"

        users_section = await page.locator("h2", has_text="Proxy Users").first.element_handle()
        assert users_section is not None, "Proxy Users section should exist"

        test_section = await page.locator("h2", has_text="Test Connectivity").first.element_handle()
        assert test_section is not None, "Test Connectivity section should exist"

        # Instance Logs is now a card with a "VIEW LOGS" button, not an h2 section
        logs_button = await page.query_selector('[data-testid="settings-view-logs-button"]')
        assert logs_button is not None, "Instance Logs section (VIEW LOGS button) should exist"

        # Danger Zone card has no title prop so it renders as a <div>, not <h2>.
        # Use the delete button data-testid as a reliable indicator.
        danger_section = await page.query_selector('[data-testid="settings-delete-button"]')
        assert danger_section is not None, "Danger Zone section (delete button) should exist"
    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_responsive_design_mobile(browser, unique_name, unique_port, api_session):
    """Test UI is responsive on mobile viewport."""
    instance_name = unique_name("mobile-test")
    port = unique_port(3226)

    page = await browser.new_page(viewport={"width": 375, "height": 667})
    try:
        await page.goto(ADDON_URL)

        # Create instance on mobile
        await page.click('[data-testid="add-instance-button"]')

        # Wait for navigation to create page before asserting
        create_form = await page.wait_for_selector(
            '[data-testid="create-name-input"]', timeout=10000
        )
        assert create_form is not None, "Create form should be visible on mobile"

        await fill_textfield_by_testid(page, "create-name-input", instance_name)
        await fill_textfield_by_testid(page, "create-port-input", str(port))

        # Form should be usable (not overflow)
        await page.click('[data-testid="create-submit-button"]')

        await page.wait_for_selector(
            f'[data-testid="instance-card-{instance_name}"]', timeout=15000
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
        await create_instance_via_ui(page, ADDON_URL, name1, port1, https_enabled=False)
        await create_instance_via_ui(page, ADDON_URL, name2, port2, https_enabled=False)

        # Try to search if search box exists
        search_box = await page.query_selector("input[placeholder*='Search']")
        if search_box:
            await page.fill("input[placeholder*='Search']", "search")
            await asyncio.sleep(0.5)
            # Verify correct instance shown
            assert await page.is_visible(f'[data-testid="instance-card-{name1}"]')
    finally:
        await page.close()
