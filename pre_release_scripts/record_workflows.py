#!/usr/bin/env python3
"""
Record user workflows as videos and convert to GIFs using Playwright.

Requirements:
    - playwright: pip install playwright
    - ffmpeg: brew install ffmpeg

Usage:
    ./record_workflows.sh <addon_url>

Example:
    ./record_workflows.sh http://localhost:8100
"""

import asyncio
import shutil  # nosec: For finding executables
import subprocess  # nosec: Controlled by user
import sys
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright

DOCS_DIR = Path(__file__).parent.parent / "docs" / "gifs"
VIDEOS_DIR = Path(tempfile.gettempdir()) / "playwright-videos"


async def record_workflow(
    browser_type,
    workflow_name: str,
    workflow_func,
    addon_url: str,
):
    """Record a workflow as a video."""

    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"🎥 Recording: {workflow_name}...")

    context = await browser_type.launch_persistent_context(
        user_data_dir=str(VIDEOS_DIR / ".profile"),
        record_video_dir=str(VIDEOS_DIR),
        viewport={"width": 1280, "height": 720},
        headless=True,
    )

    page = await context.new_page()

    try:
        await workflow_func(page, addon_url)
        print(f"  ✓ Recorded: {workflow_name}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    finally:
        await context.close()


async def workflow_dashboard(page, addon_url: str):
    """Workflow: View dashboard with instances."""
    await page.goto(f"{addon_url}/")
    await page.wait_for_load_state("networkidle")

    # Scroll to see all instances
    await page.evaluate("window.scrollBy(0, 500)")
    await asyncio.sleep(2)


async def workflow_create_proxy(page, addon_url: str):
    """Workflow: Create a new proxy instance."""
    await page.goto(f"{addon_url}/")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(1)

    # Click Add Instance
    add_btn = page.locator("button:has-text('Add Instance')")
    if await add_btn.count() > 0:
        await add_btn.click()
        await asyncio.sleep(1)

        # Fill instance name
        name_input = page.locator('input[placeholder*="name" i]')
        if await name_input.count() > 0:
            await name_input.first.fill("demo-proxy")
            await asyncio.sleep(0.5)

        # Fill port
        port_input = page.locator('input[type="number"]')
        if await port_input.count() > 0:
            await port_input.first.fill("3128")
            await asyncio.sleep(0.5)

        # Scroll to see Create button
        await page.evaluate("window.scrollBy(0, 300)")
        await asyncio.sleep(2)


async def workflow_manage_users(page, addon_url: str):
    """Workflow: Add users to a proxy."""
    await page.goto(f"{addon_url}/")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(1)

    # Click settings on first instance (if exists)
    settings_btn = page.locator("button:has-text('Settings')")
    if await settings_btn.count() > 0:
        await settings_btn.first.click()
        await asyncio.sleep(1)

        # Click Users tab
        users_tab = page.locator("button:has-text('Users')")
        if await users_tab.count() > 0:
            await users_tab.click()
            await asyncio.sleep(0.5)

            # Add user
            user_input = page.locator('input[placeholder*="username" i]')
            if await user_input.count() > 0:
                await user_input.first.fill("alice")
                await asyncio.sleep(0.3)

            pass_input = page.locator('input[type="password"]')
            if await pass_input.count() > 0:
                await pass_input.first.fill("password123")
                await asyncio.sleep(2)


async def workflow_enable_https(page, addon_url: str):
    """Workflow: Enable HTTPS on a proxy."""
    await page.goto(f"{addon_url}/")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(1)

    # Click settings
    settings_btn = page.locator("button:has-text('Settings')")
    if await settings_btn.count() > 0:
        await settings_btn.first.click()
        await asyncio.sleep(1)

        # Look for HTTPS toggle
        https_toggle = page.locator("input[type='checkbox']")
        if await https_toggle.count() > 0:
            await https_toggle.first.click()
            await asyncio.sleep(1)

            # Scroll to see HTTPS settings
            await page.evaluate("window.scrollBy(0, 300)")
            await asyncio.sleep(2)


async def workflow_view_logs(page, addon_url: str):
    """Workflow: View proxy logs."""
    await page.goto(f"{addon_url}/")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(1)

    # Click settings
    settings_btn = page.locator("button:has-text('Settings')")
    if await settings_btn.count() > 0:
        await settings_btn.first.click()
        await asyncio.sleep(1)

        # Click Logs tab
        logs_tab = page.locator("button:has-text('Logs')")
        if await logs_tab.count() > 0:
            await logs_tab.click()
            await asyncio.sleep(1)

            # Scroll through logs
            await page.evaluate("window.scrollBy(0, 200)")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollBy(0, -200)")
            await asyncio.sleep(2)


async def convert_videos_to_gifs():
    """Convert recorded videos to GIFs using ffmpeg."""
    print("\n🎬 Converting videos to GIFs...\n")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # Check if ffmpeg is available
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("⚠️  ffmpeg not found. Install with: brew install ffmpeg")
        print("Videos are saved in:", VIDEOS_DIR)
        print("\nManual conversion commands:")
        for video_file in VIDEOS_DIR.glob("*.webm"):
            gif_file = DOCS_DIR / f"{video_file.stem}.gif"
            print(
                f"  ffmpeg -i {video_file} -vf 'fps=10,scale=640:-1:flags=lanczos' -loop 0 {gif_file}"
            )
        return

    # Convert each video to GIF
    for video_file in VIDEOS_DIR.glob("*.webm"):
        gif_file = DOCS_DIR / f"{video_file.stem}.gif"

        print(f"Converting {video_file.name} → {gif_file.name}...")

        try:
            subprocess.run(  # nosec: ffmpeg_path is validated by shutil.which
                [
                    ffmpeg_path,
                    "-i",
                    str(video_file),
                    "-vf",
                    "fps=10,scale=640:-1:flags=lanczos",
                    "-loop",
                    "0",
                    str(gif_file),
                ],
                capture_output=True,
                check=True,
            )
            print(f"  ✓ Created: {gif_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Error: {e}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 record_workflows.py <addon_url>")
        print("Example: python3 record_workflows.py http://localhost:8100")
        sys.exit(1)

    addon_url = sys.argv[1].rstrip("/")

    print(f"\n🎬 Recording workflows from {addon_url}...\n")

    # Define workflows to record
    workflows = [
        ("00-dashboard", workflow_dashboard),
        ("01-create-proxy", workflow_create_proxy),
        ("02-manage-users", workflow_manage_users),
        ("03-enable-https", workflow_enable_https),
        ("04-view-logs", workflow_view_logs),
    ]

    async with async_playwright() as p:
        for workflow_name, workflow_func in workflows:
            try:
                await record_workflow(
                    p.chromium,
                    workflow_name,
                    workflow_func,
                    addon_url,
                )
            except Exception as e:
                print(f"  ✗ Failed to record {workflow_name}: {e}")

    # Convert videos to GIFs
    await convert_videos_to_gifs()

    print(f"\n✅ Done! GIFs saved to: {DOCS_DIR}\n")
    print("Update README with:")
    for gif_file in sorted(DOCS_DIR.glob("*.gif")):
        name = gif_file.stem.replace("-", " ").title()
        print(f"![{name}](docs/gifs/{gif_file.name})")


if __name__ == "__main__":
    asyncio.run(main())
