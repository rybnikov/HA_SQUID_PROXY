#!/usr/bin/env python3
"""Take screenshots of the UI to verify design fixes."""

import asyncio

from playwright.async_api import async_playwright


async def take_screenshots():
    """Take screenshots of dashboard and dialog."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        print("🔍 Navigating to http://localhost:8099...")
        await page.goto("http://localhost:8099", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Use configurable artifacts directory to avoid hardcoded /tmp paths
        import os
        import tempfile
        from pathlib import Path

        artifacts_dir = Path(os.getenv("ARTIFACTS_DIR", tempfile.gettempdir()))
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        dash_path = artifacts_dir / "01-dashboard.png"

        print("📸 Taking dashboard screenshot...")
        await page.screenshot(path=str(dash_path))
        print(f"   ✓ Saved to {dash_path}")

        print("\n🔍 Opening Add Instance dialog...")
        # Try to find and click the Add Instance button
        try:
            buttons = page.locator("button")
            count = await buttons.count()
            print(f"   Found {count} buttons on page")

            # Click the button that contains "Add Instance"
            for i in range(count):
                btn = buttons.nth(i)
                text = await btn.text_content()
                print(f"   Button {i}: {text}")
                if "Add Instance" in text:
                    print(f"   ✓ Found Add Instance button at index {i}")
                    await btn.click()
                    break
        except Exception as e:
            print(f"   ✗ Error finding button: {e}")

        await page.wait_for_timeout(1500)

        print("📸 Taking dialog screenshot...")
        dialog_path = artifacts_dir / "02-dialog.png"
        await page.screenshot(path=str(dialog_path))
        print(f"   ✓ Saved to {dialog_path}")

        # Fill form to test more states
        print("\n🔍 Filling form...")
        try:
            await page.fill("#newName", "Test Instance", timeout=3000)
            await page.fill("#newPort", "3130", timeout=3000)
            print("   ✓ Form fields filled")
        except Exception as e:
            print(f"   Note: {e}")

        await page.wait_for_timeout(500)

        print("📸 Taking filled form screenshot...")
        filled_path = artifacts_dir / "03-dialog-filled.png"
        await page.screenshot(path=str(filled_path))
        print(f"   ✓ Saved to {filled_path}")

        # Enable HTTPS checkbox
        print("\n🔍 Enabling HTTPS...")
        try:
            await page.check("#newHttps", timeout=3000)
            await page.wait_for_timeout(500)
            print("   ✓ HTTPS checkbox enabled")

            print("📸 Taking HTTPS enabled screenshot...")
            https_path = artifacts_dir / "04-dialog-https.png"
            await page.screenshot(path=str(https_path))
            print(f"   ✓ Saved to {https_path}")
        except Exception as e:
            print(f"   Note: {e}")

        print("\n✅ Screenshots captured successfully!")
        print("\n📁 Files saved:")
        print(f"   1. {dash_path} - Main dashboard view")
        print(f"   2. {dialog_path} - Dialog opened")
        print(f"   3. {filled_path} - Form filled with instance details")
        print(f"   4. {https_path} - HTTPS checkbox enabled")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(take_screenshots())
