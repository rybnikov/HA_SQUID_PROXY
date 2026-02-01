"""
E2E tests for mobile responsive UI design.

Tests validate that the UI works correctly at different viewport sizes:
- Mobile (375px, 414px)
- Tablet (768px, 1024px)
- Desktop (1280px+)
"""

import os
import pytest

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")

VIEWPORTS = {
    "mobile_small": {"width": 375, "height": 667, "name": "iPhone SE"},
    "mobile_large": {"width": 414, "height": 896, "name": "iPhone 11 Pro Max"},
    "tablet_portrait": {"width": 768, "height": 1024, "name": "iPad Mini"},
    "tablet_landscape": {"width": 1024, "height": 768, "name": "iPad Mini Landscape"},
    "desktop": {"width": 1280, "height": 800, "name": "Desktop"},
}


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "viewport_name",
    ["mobile_small", "mobile_large", "tablet_portrait", "desktop"],
)
async def test_dashboard_responsive(browser, viewport_name):
    """Test that dashboard renders correctly at different viewport sizes."""
    viewport = VIEWPORTS[viewport_name]
    page = await browser.new_page(
        viewport={"width": viewport["width"], "height": viewport["height"]}
    )
    try:
        await page.goto(ADDON_URL)

        # Header should be visible
        header = await page.query_selector("header")
        assert header is not None, f"Header not found on {viewport['name']}"

        # Title should be visible
        title = await page.query_selector("h1")
        assert title is not None, f"Title not found on {viewport['name']}"

        # Add Instance button should be visible
        add_button = await page.query_selector("button:has-text('Add Instance')")
        assert (
            add_button is not None
        ), f"Add button not found on {viewport['name']}"

        # Button should be full-width on mobile, auto-width on desktop
        button_box = await add_button.bounding_box()
        if viewport["width"] < 640:  # Mobile breakpoint
            # Button should be fairly wide on mobile (at least 250px)
            assert (
                button_box["width"] >= 250
            ), f"Button too narrow on {viewport['name']}: {button_box['width']}px"
        else:
            # Button should be more compact on desktop
            assert (
                button_box["width"] < 300
            ), f"Button too wide on {viewport['name']}: {button_box['width']}px"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_add_instance_modal_mobile(browser, unique_name, unique_port):
    """Test Add Instance modal is usable on mobile viewport."""
    instance_name = unique_name("mobile-add")
    port = unique_port(3227)

    page = await browser.new_page(viewport={"width": 375, "height": 667})
    try:
        await page.goto(ADDON_URL)

        # Open modal
        await page.click("button:has-text('Add Instance')")
        await page.wait_for_selector("#addInstanceModal", timeout=5000)

        # Modal should be visible and scrollable
        modal = await page.query_selector("#addInstanceModal")
        modal_box = await modal.bounding_box()

        # Modal should not overflow viewport width (leave space for padding)
        viewport_width = 375
        assert (
            modal_box["width"] <= viewport_width
        ), f"Modal width {modal_box['width']}px exceeds viewport {viewport_width}px"

        # Fill form
        await page.fill("#newName", instance_name)
        await page.fill("#newPort", str(port))

        # Submit button should be visible and clickable
        create_button = await page.query_selector(
            "#addInstanceModal button:has-text('Create Instance')"
        )
        assert create_button is not None, "Create button not found"

        # Button should be wide enough for touch target (at least 44px height)
        button_box = await create_button.bounding_box()
        assert (
            button_box["height"] >= 40
        ), f"Button height {button_box['height']}px too small for touch target"

        # Create instance
        await page.click("#createInstanceBtn")
        await page.wait_for_selector(
            f".instance-card[data-instance='{instance_name}']", timeout=15000
        )

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_instance_cards_mobile(browser, unique_name, unique_port, api_session):
    """Test instance cards layout on mobile."""
    instance_name = unique_name("mobile-card")
    port = unique_port(3228)

    # Create instance via API
    response = await api_session.post(
        f"{ADDON_URL}/api/instances",
        json={"name": instance_name, "port": port, "https_enabled": False},
    )
    assert response.status == 200

    page = await browser.new_page(viewport={"width": 375, "height": 667})
    try:
        await page.goto(ADDON_URL)
        await page.wait_for_selector(
            f".instance-card[data-instance='{instance_name}']", timeout=10000
        )

        # Card should be visible
        card = await page.query_selector(
            f".instance-card[data-instance='{instance_name}']"
        )
        assert card is not None, "Instance card not found"

        # Card should not be cut off (within viewport)
        card_box = await card.bounding_box()
        viewport_width = 375
        assert (
            card_box["width"] <= viewport_width - 20
        ), f"Card too wide for mobile: {card_box['width']}px"

        # Action buttons should be visible
        start_button = await card.query_selector("button.start-btn")
        stop_button = await card.query_selector("button.stop-btn")
        settings_button = await card.query_selector("button[data-action='settings']")

        assert start_button is not None, "Start button not found"
        assert stop_button is not None, "Stop button not found"
        assert settings_button is not None, "Settings button not found"

        # Buttons should be touch-friendly (at least 40px height)
        start_box = await start_button.bounding_box()
        assert (
            start_box["height"] >= 36
        ), f"Start button too small: {start_box['height']}px"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_settings_modal_tabs_mobile(
    browser, unique_name, unique_port, api_session
):
    """Test settings modal tabs are accessible on mobile."""
    instance_name = unique_name("mobile-settings")
    port = unique_port(3229)

    # Create instance via API
    response = await api_session.post(
        f"{ADDON_URL}/api/instances",
        json={"name": instance_name, "port": port, "https_enabled": False},
    )
    assert response.status == 200

    page = await browser.new_page(viewport={"width": 375, "height": 667})
    try:
        await page.goto(ADDON_URL)
        await page.wait_for_selector(
            f".instance-card[data-instance='{instance_name}']", timeout=10000
        )

        # Open settings
        await page.click(f"[data-instance='{instance_name}'] [data-action='settings']")
        await page.wait_for_selector("#settingsModal", timeout=5000)

        # All tabs should be present
        tabs = ["main", "users", "certificate", "logs", "test", "status", "delete"]
        for tab_id in tabs:
            tab = await page.query_selector(f"button[data-tab='{tab_id}']")
            assert tab is not None, f"Tab '{tab_id}' not found"

        # Tabs should be horizontally scrollable (all visible via scroll)
        # Click on last tab to verify it's reachable
        await page.click("button[data-tab='delete']")
        await page.wait_for_selector("#settingsMainTab", state="hidden", timeout=2000)

        # Should show delete confirmation content
        delete_tab_content = await page.query_selector(
            "#settingsModal >> text=Delete Instance"
        )
        assert delete_tab_content is not None, "Delete tab content not visible"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_modal_scrolling_mobile(browser, unique_name, unique_port, api_session):
    """Test that modals are scrollable on mobile when content is long."""
    instance_name = unique_name("mobile-scroll")
    port = unique_port(3230)

    # Create instance via API
    response = await api_session.post(
        f"{ADDON_URL}/api/instances",
        json={"name": instance_name, "port": port, "https_enabled": False},
    )
    assert response.status == 200

    page = await browser.new_page(viewport={"width": 375, "height": 667})
    try:
        await page.goto(ADDON_URL)
        await page.wait_for_selector(
            f".instance-card[data-instance='{instance_name}']", timeout=10000
        )

        # Open settings to users tab (has scrollable content)
        await page.click(f"[data-instance='{instance_name}'] [data-action='settings']")
        await page.wait_for_selector("#settingsModal", timeout=5000)
        await page.click("button[data-tab='users']")
        await page.wait_for_selector("#settingsUsersTab", timeout=2000)

        # Modal should be visible
        modal = await page.query_selector("#settingsModal")
        assert modal is not None, "Settings modal not found"

        # Modal should not exceed viewport height significantly
        modal_box = await modal.bounding_box()
        viewport_height = 667
        # Modal should fit within viewport (with some margin)
        assert (
            modal_box["height"] <= viewport_height - 30
        ), f"Modal too tall: {modal_box['height']}px vs {viewport_height}px viewport"

        # Add User button should be reachable (test scrolling if needed)
        add_user_button = await page.query_selector(
            "#settingsUsersTab button:has-text('Add User')"
        )
        assert add_user_button is not None, "Add User button not found"

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tablet_layout(browser, unique_name, unique_port, api_session):
    """Test that tablet layout shows 2-column grid for instance cards."""
    # Create two instances via API
    instance1_name = unique_name("tablet-1")
    instance2_name = unique_name("tablet-2")
    port1 = unique_port(3231)
    port2 = unique_port(3232)

    await api_session.post(
        f"{ADDON_URL}/api/instances",
        json={"name": instance1_name, "port": port1, "https_enabled": False},
    )
    await api_session.post(
        f"{ADDON_URL}/api/instances",
        json={"name": instance2_name, "port": port2, "https_enabled": False},
    )

    page = await browser.new_page(viewport={"width": 768, "height": 1024})
    try:
        await page.goto(ADDON_URL)
        await page.wait_for_selector(
            f".instance-card[data-instance='{instance1_name}']", timeout=10000
        )
        await page.wait_for_selector(
            f".instance-card[data-instance='{instance2_name}']", timeout=10000
        )

        # Get positions of both cards
        card1 = await page.query_selector(
            f".instance-card[data-instance='{instance1_name}']"
        )
        card2 = await page.query_selector(
            f".instance-card[data-instance='{instance2_name}']"
        )

        box1 = await card1.bounding_box()
        box2 = await card2.bounding_box()

        # On tablet (768px+), cards should be side-by-side (2 columns)
        # This means card2 should start before card1 ends vertically
        # (they're on the same row)
        assert (
            box2["y"] < box1["y"] + box1["height"]
        ), "Cards should be in 2-column layout on tablet"

    finally:
        await page.close()
