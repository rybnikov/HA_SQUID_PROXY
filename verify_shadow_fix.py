#!/usr/bin/env python3
"""Quick verification of button shadow fix."""

import asyncio
import re

from playwright.async_api import async_playwright


async def verify_button_shadow():
    """Verify button shadows are removed."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        print("\n✅ BUTTON SHADOW VERIFICATION\n")

        await page.goto("http://localhost:8099", wait_until="networkidle")
        await page.wait_for_timeout(1500)

        # Find and click Add Instance
        buttons = page.locator("button")
        count = await buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            text = await btn.text_content()
            if "Add Instance" in text:
                await btn.click()
                break

        await page.wait_for_timeout(1000)

        modal = page.locator("#addInstanceModal")
        create_btn = modal.locator("button:has-text('Create Instance')")

        if await create_btn.is_visible():
            # Get button styles
            bg = await create_btn.evaluate("el => window.getComputedStyle(el).backgroundColor")
            box_shadow = await create_btn.evaluate("el => window.getComputedStyle(el).boxShadow")

            # RGB to Hex
            rgb_match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", bg)
            if rgb_match:
                r, g, b = map(int, rgb_match.groups())
                hex_color = f"#{r:02x}{g:02x}{b:02x}"

            print("Create Instance Button:")
            print(f"  Color: {hex_color}")
            print(f"  Shadow: {box_shadow}")

            if box_shadow == "none":
                print("\n✅ FIXED: Button shadow has been removed!")
                print("   The button now has a clean appearance without colored shadow.")
            elif "rgba(0, 188, 212" in box_shadow:
                print("\n⚠️  WARNING: Cyan shadow is still present")
            else:
                print("\n✅ FIXED: Shadow is not the weird cyan color anymore")

        # Also check Cancel button
        cancel_btn = modal.locator("button:has-text('Cancel')")
        if await cancel_btn.is_visible():
            cancel_shadow = await cancel_btn.evaluate("el => window.getComputedStyle(el).boxShadow")
            print("\nCancel Button:")
            print(f"  Shadow: {cancel_shadow}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(verify_button_shadow())
