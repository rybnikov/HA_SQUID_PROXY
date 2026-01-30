#!/usr/bin/env python3
"""
Capture UI workflows as videos using Playwright.
Videos will be recorded and can be converted to GIFs for README.

Usage:
    python3 capture_workflows.py http://localhost:8100
"""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import Page, async_playwright

DOCS_DIR = Path(__file__).parent / "docs" / "gifs"


async def setup_docs_dir():
    """Create docs/gifs directory if it doesn't exist."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Using docs dir: {DOCS_DIR}")


async def workflow_create_instance(page: Page, addon_url: str):
    """Capture: Creating a new proxy instance."""
    print("Recording: Create Instance Workflow...")

    await page.goto(f"{addon_url}/")
    await page.wait_for_load_state("networkidle")

    # Click Add Instance button
    await page.click("button:has-text('Add Instance')")
    await page.wait_for_timeout(500)

    # Fill in instance name
    await page.fill('input[placeholder*="instance"]', "demo-proxy", timeout=5000)
    await page.wait_for_timeout(300)

    # Select port
    port_input = page.locator('input[type="number"]')
    await port_input.first.fill("3128")
    await page.wait_for_timeout(300)

    # Take screenshot
    await page.screenshot(path=str(DOCS_DIR / "01_create_instance_form.png"))
    print("  ✓ Saved: 01_create_instance_form.png")


async def workflow_add_users(page: Page, addon_url: str):
    """Capture: Adding users to a proxy instance."""
    print("Recording: Add Users Workflow...")

    await page.goto(f"{addon_url}/")
    await page.wait_for_load_state("networkidle")

    # Wait for instance card and click settings
    await page.wait_for_timeout(1000)
    settings_btn = page.locator("button:has-text('Settings')")
    if await settings_btn.count() > 0:
        await settings_btn.first.click()
        await page.wait_for_timeout(500)

        # Click Users tab
        users_tab = page.locator("button:has-text('Users')")
        if await users_tab.count() > 0:
            await users_tab.click()
            await page.wait_for_timeout(500)

            # Take screenshot
            await page.screenshot(path=str(DOCS_DIR / "02_manage_users.png"))
            print("  ✓ Saved: 02_manage_users.png")


async def workflow_enable_https(page: Page, addon_url: str):
    """Capture: Enabling HTTPS on an instance."""
    print("Recording: Enable HTTPS Workflow...")

    await page.goto(f"{addon_url}/")
    await page.wait_for_load_state("networkidle")

    # Wait for instance and click settings
    await page.wait_for_timeout(1000)
    settings_btn = page.locator("button:has-text('Settings')")
    if await settings_btn.count() > 0:
        await settings_btn.first.click()
        await page.wait_for_timeout(500)

        # Click General tab
        general_tab = page.locator("button:has-text('General')")
        if await general_tab.count() > 0:
            await general_tab.click()
            await page.wait_for_timeout(300)

            # Take screenshot
            await page.screenshot(path=str(DOCS_DIR / "03_https_settings.png"))
            print("  ✓ Saved: 03_https_settings.png")


async def workflow_logs(page: Page, addon_url: str):
    """Capture: Viewing logs."""
    print("Recording: View Logs Workflow...")

    await page.goto(f"{addon_url}/")
    await page.wait_for_load_state("networkidle")

    # Wait for instance and click settings
    await page.wait_for_timeout(1000)
    settings_btn = page.locator("button:has-text('Settings')")
    if await settings_btn.count() > 0:
        await settings_btn.first.click()
        await page.wait_for_timeout(500)

        # Click Logs tab
        logs_tab = page.locator("button:has-text('Logs')")
        if await logs_tab.count() > 0:
            await logs_tab.click()
            await page.wait_for_timeout(500)

            # Take screenshot
            await page.screenshot(path=str(DOCS_DIR / "04_view_logs.png"))
            print("  ✓ Saved: 04_view_logs.png")


async def workflow_dashboard(page: Page, addon_url: str):
    """Capture: Main dashboard overview."""
    print("Recording: Dashboard Overview...")

    await page.goto(f"{addon_url}/")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(1000)

    # Set viewport to show multiple cards
    await page.set_viewport_size({"width": 1280, "height": 720})

    # Take screenshot
    await page.screenshot(path=str(DOCS_DIR / "00_dashboard.png"))
    print("  ✓ Saved: 00_dashboard.png")


async def main():
    """Capture all workflows."""
    if len(sys.argv) < 2:
        print("Usage: python3 capture_workflows.py <addon_url>")
        print("Example: python3 capture_workflows.py http://localhost:8100")
        sys.exit(1)

    addon_url = sys.argv[1].rstrip("/")

    print(f"\n🎬 Capturing workflows from {addon_url}...\n")

    await setup_docs_dir()

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        try:
            # Capture main dashboard
            await workflow_dashboard(page, addon_url)

            # Capture create instance
            await workflow_create_instance(page, addon_url)

            # Capture add users
            await workflow_add_users(page, addon_url)

            # Capture HTTPS settings
            await workflow_enable_https(page, addon_url)

            # Capture logs
            await workflow_logs(page, addon_url)

            print("\n✅ All screenshots captured successfully!")
            print(f"📁 Location: {DOCS_DIR}\n")
            print("Next steps:")
            print("1. Convert PNGs to GIFs using ffmpeg:")
            print("   ffmpeg -i 00_dashboard.png -loop 0 00_dashboard.gif")
            print("\n2. Or use online tool to create animated GIFs from screenshots")
            print("3. Reference in README: ![workflow](docs/gifs/00_dashboard.gif)")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
