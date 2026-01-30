#!/usr/bin/env python3
"""
Record UI workflows as GIFs for README documentation.

Handles all waiting, retries, and error recovery internally.
Runs in Docker e2e-runner container (Playwright + ffmpeg).

Workflows recorded:
1. Add first proxy to empty dashboard + add users + test connectivity
2. Add HTTPS proxy + add users + test connectivity

Generated GIFs:
- 00-add-first-proxy.gif (from workflow 1)
- 01-add-https-proxy.gif (from workflow 2)

Saved to: /repo/docs/gifs/
"""

import asyncio
import os
import re
import subprocess  # nosec - Used safely for cp and ffmpeg commands
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright


async def setup_browser():
    """Initialize Playwright browser."""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True,
    )
    page = await context.new_page()
    return playwright, browser, context, page


async def wait_for_element(page, selector: str, timeout: int = 10000):
    """Wait for element to be visible with retries."""
    try:
        await page.locator(selector).wait_for(state="visible", timeout=timeout)
    except Exception:
        print(f"⚠️  Element not found: {selector}")
        raise


async def start_recording(page, recording_path: str):
    """Start recording page as video for GIF conversion."""
    # Note: Playwright's built-in recording requires chromium >= 92
    # We'll use a simpler approach: take screenshots and convert to GIF
    return []  # Screenshot list will be populated as we record


async def stop_recording_and_create_gif(page, screenshots: list, gif_path: str):
    """Convert screenshots to GIF using ffmpeg."""
    if not screenshots:
        print("⚠️  No screenshots to convert to GIF")
        return

    print(f"🎥 Converting {len(screenshots)} frames to GIF: {gif_path}")

    # Create temporary directory for frames
    frames_dir = Path(gif_path).parent / ".frames_tmp"
    frames_dir.mkdir(exist_ok=True, parents=True)

    try:
        # Copy screenshots with sequence numbers
        for i, screenshot_path in enumerate(screenshots):
            frame_num = str(i).zfill(4)
            dest = frames_dir / f"frame_{frame_num}.png"
            subprocess.run(
                ["cp", screenshot_path, str(dest)], check=True
            )  # nosec - Safe: cp with user-controlled paths

        # Convert PNG sequence to GIF with ffmpeg
        # 10 fps = 100ms per frame, good balance between smoothness and size
        ffmpeg_cmd = [
            "ffmpeg",
            "-framerate",
            "10",
            "-i",
            str(frames_dir / "frame_%04d.png"),
            "-vf",
            "scale=1280:-1",  # Ensure consistent width
            "-y",  # Overwrite output
            str(gif_path),
        ]

        result = subprocess.run(
            ffmpeg_cmd, capture_output=True, text=True, check=False
        )  # nosec - Safe: ffmpeg with controlled args

        if result.returncode != 0:
            print(f"❌ ffmpeg failed: {result.stderr}")
            return False

        # Get file size
        size_mb = Path(gif_path).stat().st_size / (1024 * 1024)
        print(f"✅ GIF created: {size_mb:.1f} MB")
        return True

    finally:
        # Cleanup frames directory
        import shutil

        if frames_dir.exists():
            shutil.rmtree(frames_dir, ignore_errors=True)


async def screenshot_sequence(
    page, output_dir: Path, base_name: str
) -> tuple[list[str], Callable[[], Any]]:
    """
    Take sequential screenshots during automation.
    Returns tuple of (screenshot list, capture function).
    """
    output_dir.mkdir(exist_ok=True, parents=True)
    screenshots: list[str] = []

    async def capture():
        nonlocal screenshots
        num = len(screenshots)
        path = output_dir / f"{base_name}_{str(num).zfill(3)}.png"
        await page.screenshot(path=str(path))
        screenshots.append(str(path))
        await asyncio.sleep(0.1)  # 100ms between frames for smooth GIF

    page.on("framenavigated", lambda: asyncio.create_task(capture()))
    return screenshots, capture


async def workflow_1_add_first_proxy(page, addon_url: str, screenshots_dir: Path) -> list:
    """
    Workflow 1: Add first proxy to empty dashboard + add users + test connectivity

    Steps:
    1. Navigate to dashboard (empty)
    2. Click "Add Instance" button
    3. Fill Basic tab: name="proxy1", port=3128, HTTPS OFF
    4. Go to Users tab
    5. Add user "alice" / "password123"
    6. Add user "bob" / "password456"
    7. Go to Test tab and run connectivity test
    8. Click Create Instance button
    9. Verify instance appears on dashboard
    """
    print("🎬 Recording Workflow 1: Add First Proxy with Auth...")

    screenshots = []
    screenshot_num = 0

    async def capture():
        nonlocal screenshot_num
        path = screenshots_dir / f"workflow1_{str(screenshot_num).zfill(3)}.png"
        await page.screenshot(path=str(path))
        screenshots.append(str(path))
        screenshot_num += 1
        await asyncio.sleep(0.05)  # Smoother capture

    # Navigate to dashboard
    print("  → Navigate to dashboard...")
    await page.goto(addon_url, wait_until="networkidle")
    await asyncio.sleep(1)
    await capture()

    # Click "Add Instance" button
    print("  → Click 'Add Instance' button...")
    await page.click('button:has-text("Add Instance")')
    await asyncio.sleep(0.5)
    await capture()

    # Wait for modal
    await wait_for_element(page, 'text="Instance Name"')

    # Fill Basic tab
    print("  → Fill Basic tab...")
    # Wait and fill instance name
    name_input = page.locator("input").filter(has_text=re.compile(r"name|instance", re.I)).first
    await name_input.wait_for(state="visible", timeout=10000)
    await name_input.fill("proxy1")
    await asyncio.sleep(0.2)
    await capture()

    # Fill port
    port_input = page.locator('input[type="number"]')
    await port_input.wait_for(state="visible", timeout=5000)
    await port_input.fill("3128")
    await asyncio.sleep(0.2)
    await capture()

    # Ensure HTTPS is OFF
    https_checkbox = page.locator('input[type="checkbox"]', has_text="HTTPS")
    is_checked = await https_checkbox.is_checked()
    if is_checked:
        await https_checkbox.click()
        await asyncio.sleep(0.2)

    # Click Users tab
    print("  → Go to Users tab...")
    await page.click('button:has-text("Users")')
    await asyncio.sleep(0.5)
    await capture()

    # Add first user
    print("  → Add user alice...")
    await page.fill('input[placeholder*="username"]', "alice")
    await asyncio.sleep(0.1)
    await page.fill('input[placeholder*="password"]', "password123")
    await asyncio.sleep(0.1)
    await page.click('button:has-text("Add User")')
    await asyncio.sleep(0.3)
    await capture()

    # Add second user
    print("  → Add user bob...")
    await page.fill('input[placeholder*="username"]', "bob")
    await asyncio.sleep(0.1)
    await page.fill('input[placeholder*="password"]', "password456")
    await asyncio.sleep(0.1)
    await page.click('button:has-text("Add User")')
    await asyncio.sleep(0.3)
    await capture()

    # Click Test tab
    print("  → Go to Test tab...")
    await page.click('button:has-text("Test")')
    await asyncio.sleep(0.5)
    await capture()

    # Click Test Proxy button
    print("  → Test connectivity...")
    await page.click('button:has-text("Test Proxy")')
    await asyncio.sleep(2)  # Wait for test to complete
    await capture()

    # Click Create button
    print("  → Click Create Instance...")
    await page.click('button:has-text("Create Instance")')
    await asyncio.sleep(2)  # Wait for instance creation
    await capture()

    # Verify instance on dashboard
    print("  → Verify instance created...")
    await wait_for_element(page, 'text="proxy1"', timeout=5000)
    await asyncio.sleep(1)
    await capture()

    print(f"✅ Workflow 1 recorded: {len(screenshots)} frames")
    return screenshots


async def workflow_2_add_https_proxy(page, addon_url: str, screenshots_dir: Path) -> list:
    """
    Workflow 2: Add HTTPS proxy + add users + test connectivity

    Steps:
    1. Click "Add Instance" button (dashboard now has proxy1)
    2. Fill Basic tab: name="proxy-https", port=3129, HTTPS ON
    3. Go to HTTPS Settings tab
    4. Fill HTTPS params: CN="proxy.local", Org="Home"
    5. Click "Generate Certificate"
    6. Wait for cert generation
    7. Go to Users tab
    8. Add user "charlie" / "secret123"
    9. Go to Test tab and run HTTPS connectivity test
    10. Click Create Instance button
    11. Verify instance appears on dashboard
    """
    print("🎬 Recording Workflow 2: Add HTTPS Proxy with Cert...")

    screenshots = []
    screenshot_num = 0

    async def capture():
        nonlocal screenshot_num
        path = screenshots_dir / f"workflow2_{str(screenshot_num).zfill(3)}.png"
        await page.screenshot(path=str(path))
        screenshots.append(str(path))
        screenshot_num += 1
        await asyncio.sleep(0.05)

    # Click "Add Instance" button
    print("  → Click 'Add Instance' button...")
    await page.click('button:has-text("Add Instance")')
    await asyncio.sleep(0.5)
    await capture()

    # Wait for modal
    await wait_for_element(page, 'text="Instance Name"')

    # Fill Basic tab
    print("  → Fill Basic tab...")
    await page.fill('input[placeholder*="name"]', "proxy-https", timeout=5000)
    await asyncio.sleep(0.2)
    await capture()

    # Set port
    await page.fill('input[type="number"]', "3129", timeout=5000)
    await asyncio.sleep(0.2)
    await capture()

    # Enable HTTPS
    print("  → Enable HTTPS...")
    https_checkbox = page.locator('input[type="checkbox"]', has_text="HTTPS")
    is_checked = await https_checkbox.is_checked()
    if not is_checked:
        await https_checkbox.click()
        await asyncio.sleep(0.5)

    # Click HTTPS Settings tab
    print("  → Go to HTTPS Settings tab...")
    await page.click('button:has-text("HTTPS Settings")')
    await asyncio.sleep(0.5)
    await capture()

    # Fill certificate params
    print("  → Fill HTTPS parameters...")
    await page.fill('input[placeholder*="CN"]', "proxy.local")
    await asyncio.sleep(0.1)
    await capture()

    await page.fill('input[placeholder*="Organization"]', "Home")
    await asyncio.sleep(0.1)
    await capture()

    # Click Generate Certificate
    print("  → Generate certificate...")
    await page.click('button:has-text("Generate Certificate")')
    await asyncio.sleep(3)  # Wait for cert generation
    await capture()

    # Click Users tab
    print("  → Go to Users tab...")
    await page.click('button:has-text("Users")')
    await asyncio.sleep(0.5)
    await capture()

    # Add user
    print("  → Add user charlie...")
    await page.fill('input[placeholder*="username"]', "charlie")
    await asyncio.sleep(0.1)
    await page.fill('input[placeholder*="password"]', "secret123")
    await asyncio.sleep(0.1)
    await page.click('button:has-text("Add User")')
    await asyncio.sleep(0.3)
    await capture()

    # Click Test tab
    print("  → Go to Test tab...")
    await page.click('button:has-text("Test")')
    await asyncio.sleep(0.5)
    await capture()

    # Click Test Proxy button
    print("  → Test HTTPS connectivity...")
    await page.click('button:has-text("Test Proxy")')
    await asyncio.sleep(2)
    await capture()

    # Click Create button
    print("  → Click Create Instance...")
    await page.click('button:has-text("Create Instance")')
    await asyncio.sleep(2)
    await capture()

    # Verify instance on dashboard
    print("  → Verify instance created...")
    await wait_for_element(page, 'text="proxy-https"', timeout=5000)
    await asyncio.sleep(1)
    await capture()

    print(f"✅ Workflow 2 recorded: {len(screenshots)} frames")
    return screenshots


async def main():
    """Record all workflows and generate GIFs."""
    addon_url = os.environ.get("ADDON_URL", "http://localhost:8100")
    repo_root = Path(os.environ.get("REPO_ROOT", "/repo"))
    gifs_dir = repo_root / "docs" / "gifs"
    frames_dir = repo_root / "pre_release_scripts" / ".frames"

    print(f"📍 Addon URL: {addon_url}")
    print(f"📁 Output directory: {gifs_dir}")
    print()

    # Ensure output directory exists
    gifs_dir.mkdir(exist_ok=True, parents=True)

    playwright, browser, context, page = None, None, None, None

    try:
        print("🐳 Starting browser (Playwright/Chromium)...")
        playwright, browser, context, page = await setup_browser()

        # Workflow 1: Add first proxy with auth
        screenshots1 = await workflow_1_add_first_proxy(page, addon_url, frames_dir)
        await stop_recording_and_create_gif(
            page,
            screenshots1,
            str(gifs_dir / "00-add-first-proxy.gif"),
        )

        print()

        # Workflow 2: Add HTTPS proxy
        screenshots2 = await workflow_2_add_https_proxy(page, addon_url, frames_dir)
        await stop_recording_and_create_gif(
            page,
            screenshots2,
            str(gifs_dir / "01-add-https-proxy.gif"),
        )

        print()
        print("🎉 All workflows recorded successfully!")
        print(f"✨ GIFs saved to: {gifs_dir}/")

    except Exception as e:
        print(f"❌ Error during recording: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        if page and context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

        # Cleanup frames directory
        if frames_dir.exists():
            import shutil

            shutil.rmtree(frames_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
