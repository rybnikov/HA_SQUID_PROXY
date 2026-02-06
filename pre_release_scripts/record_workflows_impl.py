#!/usr/bin/env python3
"""
Record UI workflows as GIFs for README documentation.

Handles all waiting, retries, and error recovery internally.
Can run locally or in Docker e2e-runner container (Playwright + ffmpeg).

When HA_URL is set, records from within Home Assistant UI (with sidebar).
Otherwise records from the standalone addon URL.

Workflows recorded:
1. Add first proxy to empty dashboard + add users + test connectivity
2. Add HTTPS proxy + add users + test connectivity

Generated GIFs:
- 00-add-first-proxy.gif (from workflow 1)
- 01-add-https-proxy.gif (from workflow 2)

Saved to: docs/gifs/
"""

from __future__ import annotations

import asyncio
import os
import subprocess  # nosec - Used safely for cp and ffmpeg commands
import sys
from pathlib import Path

from playwright.async_api import Page, async_playwright

SLOW_FACTOR = float(os.environ.get("RECORDING_SLOW_FACTOR", "1"))
MIN_ACTION_PAUSE = float(os.environ.get("RECORDING_MIN_ACTION_PAUSE", "2"))
GIF_FPS = int(os.environ.get("RECORDING_GIF_FPS", "1"))


async def slow_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds * SLOW_FACTOR)


async def pause_between_actions(capture, seconds: float | None = None) -> None:
    duration = seconds if seconds is not None else MIN_ACTION_PAUSE
    steps = max(1, int(duration * GIF_FPS))
    step_seconds = duration / steps
    for _ in range(steps):
        await asyncio.sleep(step_seconds)
        await capture()


async def capture_and_pause(capture, seconds: float | None = None) -> None:
    await capture()
    await pause_between_actions(capture, seconds)


async def fill_field(page: Page, testid: str, value: str, timeout: int = 10000) -> None:
    """Fill a text field by targeting its inner input element.

    Works for both HA native components (ha-textfield with shadow DOM)
    and fallback HTML inputs. Playwright CSS selectors pierce shadow DOM.
    """
    inner = page.locator(f'[data-testid="{testid}"] input')
    if await inner.count():
        await inner.fill(value, timeout=timeout)
    else:
        await page.locator(f'[data-testid="{testid}"]').fill(value, timeout=timeout)


async def click_checkbox(page: Page, testid: str) -> None:
    """Click a switch/checkbox by targeting its inner input element."""
    checkbox = page.locator(f'[data-testid="{testid}"] input[type="checkbox"]')
    if await checkbox.count():
        await checkbox.click()
    else:
        await page.click(f'[data-testid="{testid}"]')


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


async def ha_login(page: Page, ha_url: str, username: str, password: str) -> None:
    """Log into Home Assistant via the login page."""
    print(f"  Logging into Home Assistant at {ha_url}...")
    await page.goto(ha_url, wait_until="networkidle")
    await slow_sleep(2)

    # HA login page has username and password fields
    try:
        await page.wait_for_selector('input[name="username"], input[type="text"]', timeout=15000)
    except Exception:
        print("  Login form not found, might already be authenticated")
        return

    # Fill username and password
    await page.locator('input[name="username"]').fill(username)
    await slow_sleep(0.5)
    await page.locator('input[type="password"]').fill(password)
    await slow_sleep(0.5)

    # Click the "Log in" button (HA uses custom button elements)
    await page.locator('text="Log in"').click()

    # Wait for navigation to complete (HA redirects to overview)
    await slow_sleep(4)
    print("  Logged in successfully")


async def navigate_to_panel(page: Page, ha_url: str, panel_path: str) -> None:
    """Navigate to the Squid Proxy Manager panel in HA via sidebar."""
    print(f"  Navigating to panel: /{panel_path}")

    # Use sidebar link (force click to bypass web component overlay)
    sidebar_link = page.locator(f'a[href="/{panel_path}"]')
    if await sidebar_link.count():
        await sidebar_link.first.click(force=True)
    else:
        # Fallback: direct navigation
        await page.goto(f"{ha_url}/{panel_path}", wait_until="networkidle")

    await slow_sleep(3)

    # Wait for the panel to render (our React app inside HA shell)
    await page.wait_for_selector(
        '[data-testid="add-instance-button"], [data-testid="empty-state-add-button"]',
        timeout=15000,
    )
    print("  Panel loaded")


async def wait_for_element(page: Page, selector: str, timeout: int = 10000):
    """Wait for element to be visible with retries."""
    try:
        await page.locator(selector).wait_for(state="visible", timeout=timeout)
    except Exception:
        print(f"  Element not found: {selector}")
        raise


async def stop_recording_and_create_gif(page: Page, screenshots: list, gif_path: str):
    """Convert screenshots to GIF using ffmpeg."""
    if not screenshots:
        print("  No screenshots to convert to GIF")
        return

    print(f"  Converting {len(screenshots)} frames to GIF: {gif_path}")

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

        # Convert PNG sequence to GIF with ffmpeg (slower + smaller)
        ffmpeg_cmd = [
            "ffmpeg",
            "-framerate",
            str(GIF_FPS),
            "-i",
            str(frames_dir / "frame_%04d.png"),
            "-vf",
            f"fps={GIF_FPS},scale=1024:-1:flags=lanczos,split[s0][s1];"
            "[s0]palettegen=max_colors=128[p];"
            "[s1][p]paletteuse=dither=bayer:bayer_scale=5",
            "-y",  # Overwrite output
            str(gif_path),
        ]

        result = subprocess.run(
            ffmpeg_cmd, capture_output=True, text=True, check=False
        )  # nosec - Safe: ffmpeg with controlled args

        if result.returncode != 0:
            print(f"  ffmpeg failed: {result.stderr}")
            return False

        # Get file size
        size_mb = Path(gif_path).stat().st_size / (1024 * 1024)
        print(f"  GIF created: {size_mb:.1f} MB")
        return True

    finally:
        # Cleanup frames directory
        import shutil

        if frames_dir.exists():
            shutil.rmtree(frames_dir, ignore_errors=True)


async def workflow_1_add_first_proxy(page: Page, screenshots_dir: Path) -> list:
    """
    Workflow 1: Add first proxy to empty dashboard + add users + test connectivity

    Steps:
    1. See empty dashboard
    2. Click "Add Instance" button
    3. Fill form: name="proxy1", port=3128, HTTPS OFF
    4. Click Create Instance button
    5. Navigate to settings for the new instance
    6. Add users "alice" and "bob"
    7. Test connectivity
    8. Return to dashboard
    """
    print("Recording Workflow 1: Add First Proxy with Auth...")

    screenshots = []
    screenshot_num = 0

    async def capture():
        nonlocal screenshot_num
        path = screenshots_dir / f"workflow1_{str(screenshot_num).zfill(3)}.png"
        await page.screenshot(path=str(path))
        screenshots.append(str(path))
        screenshot_num += 1
        await slow_sleep(0.35)

    # Capture the empty dashboard
    print("  -> Empty dashboard...")
    await slow_sleep(1.2)
    await capture_and_pause(capture)

    # Click "Add Instance" button
    print("  -> Click 'Add Instance' button...")
    await page.click('[data-testid="add-instance-button"]')
    await slow_sleep(1.2)
    await capture_and_pause(capture)

    # Wait for create page to load
    await wait_for_element(page, '[data-testid="create-instance-form"]')

    # Fill instance name
    print("  -> Fill basic fields...")
    await page.locator('[data-testid="create-name-input"]').wait_for(state="visible", timeout=10000)
    await fill_field(page, "create-name-input", "proxy1")
    await slow_sleep(0.6)
    await capture_and_pause(capture)

    # Fill port
    await page.locator('[data-testid="create-port-input"]').wait_for(state="visible", timeout=5000)
    await fill_field(page, "create-port-input", "3128")
    await slow_sleep(0.6)
    await capture_and_pause(capture)

    # Click Create Instance button
    print("  -> Click Create Instance...")
    await page.click('[data-testid="create-submit-button"]')
    await slow_sleep(2.6)
    await capture_and_pause(capture)

    # Should redirect to dashboard - verify instance exists
    print("  -> Verify instance created...")
    await page.locator('[data-testid="instance-card-proxy1"]').wait_for(
        state="visible", timeout=8000
    )
    await slow_sleep(1.2)
    await capture_and_pause(capture)

    # Navigate to settings
    print("  -> Open Settings...")
    await page.click('[data-testid="instance-settings-chip-proxy1"]')
    await slow_sleep(1.2)
    await capture_and_pause(capture)

    # Wait for settings page to load
    await wait_for_element(page, '[data-testid="settings-tabs"]')

    # Scroll to Users section
    print("  -> Scroll to Users section...")
    await page.locator('[data-testid="user-username-input"]').scroll_into_view_if_needed()
    await slow_sleep(0.8)
    await capture_and_pause(capture)

    # Add first user - alice
    print("  -> Add user alice...")
    await fill_field(page, "user-username-input", "alice")
    await slow_sleep(0.5)
    await fill_field(page, "user-password-input", "password123")
    await slow_sleep(0.5)
    await page.click('[data-testid="user-add-button"]')
    await slow_sleep(0.8)
    await capture_and_pause(capture)

    # Add second user - bob
    print("  -> Add user bob...")
    await fill_field(page, "user-username-input", "bob")
    await slow_sleep(0.5)
    await fill_field(page, "user-password-input", "password456")
    await slow_sleep(0.5)
    await page.click('[data-testid="user-add-button"]')
    await slow_sleep(0.8)
    await capture_and_pause(capture)

    # Scroll to Test Connectivity section
    print("  -> Scroll to Test section...")
    await page.locator('[data-testid="test-username-input"]').scroll_into_view_if_needed()
    await slow_sleep(0.8)
    await capture_and_pause(capture)

    # Test connectivity
    print("  -> Test connectivity...")
    await fill_field(page, "test-username-input", "alice")
    await slow_sleep(0.5)
    await fill_field(page, "test-password-input", "password123")
    await slow_sleep(0.5)
    await fill_field(page, "test-url-input", "http://example.com")
    await slow_sleep(0.5)
    await page.click('[data-testid="test-button"]')
    await slow_sleep(4)  # Wait for test to complete
    await capture_and_pause(capture)

    # Return to dashboard
    print("  -> Return to dashboard...")
    await page.go_back()
    await slow_sleep(1.2)
    await capture_and_pause(capture)

    print(f"  Workflow 1 recorded: {len(screenshots)} frames")
    return screenshots


async def workflow_2_add_https_proxy(page: Page, screenshots_dir: Path) -> list:
    """
    Workflow 2: Add HTTPS proxy + add users + test connectivity

    Steps:
    1. Click "Add Instance" button (dashboard now has proxy1)
    2. Fill form: name="proxy-https", port=3129, HTTPS ON
    3. Click Create Instance
    4. Navigate to settings for the HTTPS instance
    5. Regenerate certificate
    6. Add user "charlie"
    7. Test connectivity
    """
    print("Recording Workflow 2: Add HTTPS Proxy with Cert...")

    screenshots = []
    screenshot_num = 0

    async def capture():
        nonlocal screenshot_num
        path = screenshots_dir / f"workflow2_{str(screenshot_num).zfill(3)}.png"
        await page.screenshot(path=str(path))
        screenshots.append(str(path))
        screenshot_num += 1
        await slow_sleep(0.35)

    # Click "Add Instance" button in top bar
    print("  -> Click 'Add Instance' button...")
    await page.click('[data-testid="add-instance-button"]')
    await slow_sleep(0.5)
    await capture_and_pause(capture)

    # Wait for create page
    await wait_for_element(page, '[data-testid="create-instance-form"]')

    # Fill instance name
    print("  -> Fill basic fields...")
    await fill_field(page, "create-name-input", "proxy-https")
    await slow_sleep(0.6)
    await capture_and_pause(capture)

    # Set port
    await fill_field(page, "create-port-input", "3129")
    await slow_sleep(0.6)
    await capture_and_pause(capture)

    # Enable HTTPS
    print("  -> Enable HTTPS...")
    await click_checkbox(page, "create-https-switch")
    await slow_sleep(1.2)
    await capture_and_pause(capture)

    # Click Create Instance button
    print("  -> Click Create Instance...")
    await page.click('[data-testid="create-submit-button"]')
    await slow_sleep(2.6)
    await capture_and_pause(capture)

    # Verify instance on dashboard
    print("  -> Verify instance created...")
    await page.locator('[data-testid="instance-card-proxy-https"]').wait_for(
        state="visible", timeout=8000
    )
    await slow_sleep(1.2)
    await capture_and_pause(capture)

    # Navigate to settings
    print("  -> Open Settings...")
    await page.click('[data-testid="instance-settings-chip-proxy-https"]')
    await slow_sleep(1.2)
    await capture_and_pause(capture)

    # Wait for settings page
    await wait_for_element(page, '[data-testid="settings-tabs"]')

    # Regenerate certificate
    print("  -> Regenerate certificate...")
    await page.locator('[data-testid="cert-regenerate-button"]').scroll_into_view_if_needed()
    await slow_sleep(0.5)
    await page.click('[data-testid="cert-regenerate-button"]')
    await slow_sleep(4)
    await capture_and_pause(capture)

    # Add user
    print("  -> Add user charlie...")
    await page.locator('[data-testid="user-username-input"]').scroll_into_view_if_needed()
    await slow_sleep(0.5)
    await fill_field(page, "user-username-input", "charlie")
    await slow_sleep(0.5)
    await fill_field(page, "user-password-input", "secret123")
    await slow_sleep(0.5)
    await page.click('[data-testid="user-add-button"]')
    await slow_sleep(0.8)
    await capture_and_pause(capture)

    # Test connectivity
    print("  -> Test HTTPS connectivity...")
    await page.locator('[data-testid="test-username-input"]').scroll_into_view_if_needed()
    await slow_sleep(0.5)
    await fill_field(page, "test-username-input", "charlie")
    await slow_sleep(0.5)
    await fill_field(page, "test-password-input", "secret123")
    await slow_sleep(0.5)
    await fill_field(page, "test-url-input", "https://example.com")
    await slow_sleep(0.5)
    await page.click('[data-testid="test-button"]')
    await slow_sleep(4)
    await capture_and_pause(capture)

    print(f"  Workflow 2 recorded: {len(screenshots)} frames")
    return screenshots


async def main():
    """Record all workflows and generate GIFs."""
    addon_url = os.environ.get("ADDON_URL", "http://localhost:8099")
    ha_url = os.environ.get("HA_URL", "")
    ha_username = os.environ.get("HA_USERNAME", "recorder")
    ha_password = os.environ.get("HA_PASSWORD", "recorder123")
    ha_panel_path = os.environ.get("HA_PANEL_PATH", "squid-proxy-manager")
    repo_root = Path(os.environ.get("REPO_ROOT", str(Path(__file__).resolve().parent.parent)))
    gifs_dir = repo_root / "docs" / "gifs"
    frames_dir = repo_root / "pre_release_scripts" / ".frames"

    use_ha = bool(ha_url)

    if use_ha:
        print("HA Mode: Recording from within Home Assistant")
        print(f"HA URL: {ha_url}")
        print(f"Panel path: {ha_panel_path}")
    else:
        print("Standalone Mode: Recording from addon directly")
        print(f"Addon URL: {addon_url}")
    print(f"Output directory: {gifs_dir}")
    print()

    # Ensure output directory exists
    gifs_dir.mkdir(exist_ok=True, parents=True)
    frames_dir.mkdir(exist_ok=True, parents=True)

    playwright, browser, context, page = None, None, None, None

    try:
        print("Starting browser (Playwright/Chromium)...")
        playwright, browser, context, page = await setup_browser()

        if use_ha:
            # Log into Home Assistant
            await ha_login(page, ha_url, ha_username, ha_password)
            # Navigate to the panel
            await navigate_to_panel(page, ha_url, ha_panel_path)
        else:
            # Navigate to standalone addon
            await page.goto(addon_url, wait_until="networkidle")
            await slow_sleep(1.2)

        # Workflow 1: Add first proxy with auth
        screenshots1 = await workflow_1_add_first_proxy(page, frames_dir)
        await stop_recording_and_create_gif(
            page,
            screenshots1,
            str(gifs_dir / "00-add-first-proxy.gif"),
        )

        print()

        # Workflow 2: Add HTTPS proxy
        screenshots2 = await workflow_2_add_https_proxy(page, frames_dir)
        await stop_recording_and_create_gif(
            page,
            screenshots2,
            str(gifs_dir / "01-add-https-proxy.gif"),
        )

        print()
        print("All workflows recorded successfully!")
        print(f"GIFs saved to: {gifs_dir}/")

    except Exception as e:
        print(f"Error during recording: {e}")
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
