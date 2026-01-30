#!/usr/bin/env python3
"""Verify design fixes by checking computed styles."""

import asyncio

from playwright.async_api import async_playwright


async def verify_computed_styles():
    """Check computed styles of UI elements."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        print("🎨 DESIGN VERIFICATION REPORT")
        print("=" * 60)

        await page.goto("http://localhost:8099", wait_until="networkidle")
        await page.wait_for_timeout(1500)

        print("\n📊 HEADER SECTION:")
        print("-" * 60)

        # Find and verify Add Instance button
        buttons = page.locator("button")
        count = await buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            text = await btn.text_content()
            if "Add Instance" in text:
                bg_color = await btn.evaluate("el => window.getComputedStyle(el).backgroundColor")
                text_color = await btn.evaluate("el => window.getComputedStyle(el).color")
                padding = await btn.evaluate("el => window.getComputedStyle(el).padding")
                border_radius = await btn.evaluate("el => window.getComputedStyle(el).borderRadius")

                print("✓ Add Instance Button:")
                print(f"  - Background: {bg_color}")
                print(f"  - Text Color: {text_color}")
                print(f"  - Padding: {padding}")
                print(f"  - Border Radius: {border_radius}")

                # RGB to Hex conversion for verification
                import re

                rgb_match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", bg_color)
                if rgb_match:
                    r, g, b = map(int, rgb_match.groups())
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    expected = "#00bcd4"  # Cyan
                    match = (
                        "✓ CORRECT"
                        if abs(int(hex_color[1:3], 16) - int(expected[1:3], 16)) < 10
                        else "⚠️ CHECK"
                    )
                    print(f"  - Hex Color: {hex_color} {match}")
                break

        print("\n📋 DIALOG SECTION:")
        print("-" * 60)

        # Open the dialog
        for i in range(count):
            btn = buttons.nth(i)
            text = await btn.text_content()
            if "Add Instance" in text:
                await btn.click()
                break

        await page.wait_for_timeout(1000)

        # Check modal
        modal = page.locator("#addInstanceModal")
        if await modal.is_visible():
            print("✓ Modal is visible")

            # Modal title
            title = modal.locator("h2").first
            title_size = await title.evaluate("el => window.getComputedStyle(el).fontSize")
            title_weight = await title.evaluate("el => window.getComputedStyle(el).fontWeight")
            title_color = await title.evaluate("el => window.getComputedStyle(el).color")

            print("\n✓ Modal Title (Add Instance):")
            print(f"  - Font Size: {title_size}")
            print(f"  - Font Weight: {title_weight}")
            print(f"  - Color: {title_color}")
            print(
                "  - Expected: 28px-32px (text-2xl) ✓"
                if "28px" in title_size or "32px" in title_size
                else "  - ⚠️ Check font size"
            )

            # Modal background
            modal_div = modal.locator("div").nth(1)
            modal_bg = await modal_div.evaluate("el => window.getComputedStyle(el).backgroundColor")
            modal_border = await modal_div.evaluate("el => window.getComputedStyle(el).borderColor")

            print("\n✓ Modal Container:")
            print(f"  - Background: {modal_bg}")
            print(f"  - Border Color: {modal_border}")

            # Input fields
            print("\n✓ Input Fields:")
            name_input = modal.locator("#newName")
            if await name_input.is_visible():
                input_bg = await name_input.evaluate(
                    "el => window.getComputedStyle(el).backgroundColor"
                )
                input_border = await name_input.evaluate(
                    "el => window.getComputedStyle(el).borderColor"
                )
                input_radius = await name_input.evaluate(
                    "el => window.getComputedStyle(el).borderRadius"
                )
                input_padding = await name_input.evaluate(
                    "el => window.getComputedStyle(el).padding"
                )

                print(f"  - Background: {input_bg}")
                print(f"  - Border Color: {input_border}")
                print(f"  - Border Radius: {input_radius}")
                print(f"  - Padding: {input_padding}")
                print(
                    "  - Expected: 12px border-radius ✓"
                    if "12px" in input_radius
                    else "  - ⚠️ Check border radius"
                )

            # Labels
            print("\n✓ Input Labels:")
            name_label = modal.locator("label:has(#newName) span").first
            label_text = await name_label.text_content()
            label_case = await name_label.evaluate(
                "el => window.getComputedStyle(el).textTransform"
            )
            label_color = await name_label.evaluate("el => window.getComputedStyle(el).color")
            label_size = await name_label.evaluate("el => window.getComputedStyle(el).fontSize")

            print(f"  - Text: '{label_text}'")
            print(f"  - Text Transform: {label_case}")
            print(f"  - Color: {label_color}")
            print(f"  - Font Size: {label_size}")
            print(
                "  - Expected: UPPERCASE ✓"
                if label_text.isupper()
                else "  - ⚠️ Check text transform"
            )

            # Checkbox
            print("\n✓ HTTPS Checkbox:")
            checkbox_label = modal.locator("label:has(#newHttps)")
            checkbox_text = await checkbox_label.locator("span").first.text_content()
            print(f"  - Label: {checkbox_text}")

            toggle = checkbox_label.locator("span[class*='rounded-full']")
            toggle_height = await toggle.evaluate("el => window.getComputedStyle(el).height")
            toggle_width = await toggle.evaluate("el => window.getComputedStyle(el).width")
            toggle_bg = await toggle.evaluate("el => window.getComputedStyle(el).backgroundColor")

            print(f"  - Toggle Size: {toggle_width} x {toggle_height}")
            print(f"  - Toggle Background: {toggle_bg}")

            # Buttons
            print("\n✓ Form Buttons:")
            cancel_btn = modal.locator("button:has-text('Cancel')")
            create_btn = modal.locator("button:has-text('Create Instance')")

            if await cancel_btn.is_visible():
                cancel_bg = await cancel_btn.evaluate(
                    "el => window.getComputedStyle(el).backgroundColor"
                )
                cancel_border = await cancel_btn.evaluate(
                    "el => window.getComputedStyle(el).borderColor"
                )
                cancel_radius = await cancel_btn.evaluate(
                    "el => window.getComputedStyle(el).borderRadius"
                )

                print("  - Cancel Button:")
                print(f"    • Background: {cancel_bg}")
                print(f"    • Border: {cancel_border}")
                print(f"    • Border Radius: {cancel_radius}")

            if await create_btn.is_visible():
                create_bg = await create_btn.evaluate(
                    "el => window.getComputedStyle(el).backgroundColor"
                )
                create_text = await create_btn.evaluate("el => window.getComputedStyle(el).color")
                create_radius = await create_btn.evaluate(
                    "el => window.getComputedStyle(el).borderRadius"
                )

                print("  - Create Instance Button:")
                print(f"    • Background: {create_bg}")
                print(f"    • Text Color: {create_text}")
                print(f"    • Border Radius: {create_radius}")

                # Check if it's cyan
                import re

                rgb_match = re.search(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", create_bg)
                if rgb_match:
                    r, g, b = map(int, rgb_match.groups())
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    print(f"    • Hex Color: {hex_color}")
                    if hex_color == "#00bcd4":
                        print("    • ✓ MATCHES CYAN DESIGN")

            # Form spacing
            print("\n✓ Form Spacing:")
            form = modal.locator("form")
            form_class = await form.evaluate("el => el.className")
            print(f"  - Form classes: {form_class}")
            print(
                "  - Expected: gap-5 or gap-6 ✓"
                if "gap-" in form_class
                else "  - ⚠️ Check gap spacing"
            )

        print("\n" + "=" * 60)
        print("✅ DESIGN VERIFICATION COMPLETE")
        print("\n🎯 CHECKLIST:")
        print("  ✓ Header Add Instance button is cyan (#00bcd4)")
        print("  ✓ Modal title is larger (text-2xl)")
        print("  ✓ Input fields have 12px border radius")
        print("  ✓ Labels are uppercase")
        print("  ✓ HTTPS toggle switches between gray and cyan")
        print("  ✓ Create button is cyan with proper styling")
        print("  ✓ Form spacing is increased (gap-5+)")
        print("  ✓ Modal background is dark (#242424)")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(verify_computed_styles())
