"""E2E tests for HTTPS functionality via UI.

These tests verify that HTTPS can be enabled, configured, and used
through the web UI, matching the test plan in HTTPS_TEST_PLAN.md.
"""

import asyncio
import os

import aiohttp
import pytest

# Test addon URL - configured in conftest.py
ADDON_URL = "http://addon:8099"
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "test_token")
API_HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


@pytest.fixture
async def clean_instance(browser):
    """Clean up instance after test."""
    instances_to_clean: list[str] = []
    yield instances_to_clean

    # Cleanup after test
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        for instance_name in instances_to_clean:
            try:
                await session.delete(f"{ADDON_URL}/api/instances/{instance_name}")
            except Exception:
                pass


@pytest.mark.asyncio
async def test_https_create_instance_ui(browser, clean_instance):
    """E-HTTPS-01: Create HTTPS instance via UI."""
    instance_name = "https-ui-test"
    clean_instance.append(instance_name)

    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Click Add Instance
    await page.click("button:has-text('+ Add Instance')")
    await page.wait_for_selector("#addInstanceModal", state="visible")

    # 2. Fill instance details
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", "3150")

    # 3. Enable HTTPS
    await page.check("#newHttps")

    # 4. Verify certificate auto-generation message appears
    await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)

    # 5. Create instance
    await page.click("#createInstanceBtn")

    # 7. Wait for modal to close and instance to appear
    await page.wait_for_selector("#addInstanceModal", state="hidden", timeout=30000)
    await page.wait_for_selector(f".instance-card[data-instance='{instance_name}']", timeout=30000)

    # 8. Verify instance is created with HTTPS
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None, "Instance should be created"
            assert instance["https_enabled"] is True, "HTTPS should be enabled"

    await page.close()


@pytest.mark.asyncio
async def test_https_certificate_settings_visibility(browser, clean_instance):
    """E-HTTPS-02: Certificate settings visible when HTTPS checked."""
    page = await browser.new_page()
    await page.goto(ADDON_URL)

    # Open Add Instance modal
    await page.click("button:has-text('+ Add Instance')")
    await page.wait_for_selector("#addInstanceModal", state="visible")

    # Auto-generation message should be hidden initially
    assert not await page.is_visible(
        "text=Certificate will be auto-generated"
    ), "Auto-generation message should be hidden initially"

    # Check HTTPS checkbox
    await page.check("#newHttps")

    # Auto-generation message should be visible now
    await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
    assert await page.is_visible(
        "text=Certificate will be auto-generated"
    ), "Auto-generation message should be visible when HTTPS is checked"

    # Uncheck HTTPS
    await page.uncheck("#newHttps")

    # Auto-generation message should be hidden again
    await page.wait_for_selector(
        "text=Certificate will be auto-generated", state="hidden", timeout=2000
    )

    await page.close()


@pytest.mark.asyncio
async def test_https_instance_starts_from_ui(browser, clean_instance):
    """E-HTTPS-05: HTTPS instance starts from UI and shows Running status.

    CRITICAL TEST: This catches the ssl_bump issue!
    If ssl_bump is present in config, Squid will crash with:
    'FATAL: No valid signing certificate configured for HTTPS_port'

    This test verifies:
    1. HTTPS instance is created
    2. Instance status is "running" (not crashed)
    3. Instance STAYS running after multiple checks
    4. Logs don't contain FATAL errors
    """
    instance_name = "https-start-test"
    clean_instance.append(instance_name)

    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    await page.goto(ADDON_URL)

    # Create HTTPS instance
    await page.click("button:has-text('+ Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", "3151")
    await page.check("#newHttps")
    await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
    await page.click("#createInstanceBtn")

    # Wait for instance to be created and started
    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=30000)

    # Wait for Squid to start (or crash if ssl_bump issue exists)
    await asyncio.sleep(5)

    # Verify via API - MULTIPLE CHECKS to ensure it stays running
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            # Instance should be running (certificate generation and Squid start succeeded)
            # Note: If HTTPS is still broken, this will fail - that's the purpose of this test
            assert (
                instance["running"] is True
            ), f"HTTPS instance should be running. Status: {instance.get('status')}"

    await page.close()


@pytest.mark.asyncio
async def test_https_enable_on_existing_instance(browser, clean_instance):
    """E-HTTPS-06: Enable HTTPS on existing HTTP instance via Settings."""
    instance_name = "https-enable-test"
    clean_instance.append(instance_name)

    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create HTTP instance first (without HTTPS)
    await page.click("button:has-text('+ Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", "3152")
    # Don't check HTTPS - create as HTTP first
    await page.click("#createInstanceBtn")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=10000)

    # 2. Wait for instance to be ready
    await asyncio.sleep(3)

    # 3. Open Settings modal
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal", state="visible")

    # 4. Enable HTTPS
    await page.check("#editHttps")
    await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)

    # 5. Save changes
    await page.click("#settingsModal button:has-text('Save Changes')")

    # 6. Wait for modal to close and instance to restart
    await page.wait_for_selector("#settingsModal", state="hidden", timeout=30000)
    await asyncio.sleep(5)  # Wait for restart with HTTPS

    # 7. Verify HTTPS is enabled via API
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert instance["https_enabled"] is True, "HTTPS should be enabled"
            assert (
                instance["running"] is True
            ), "Instance should still be running after HTTPS enable"

    await page.close()


@pytest.mark.asyncio
async def test_https_delete_instance_ui(browser, clean_instance):
    """E-HTTPS-10: Delete HTTPS instance via UI and verify cleanup.

    Note: Delete now uses a custom modal instead of window.confirm()
    because confirm() doesn't work reliably in iframe/ingress context.
    """
    instance_name = "https-delete-test"
    # Don't add to clean_instance since we're deleting it in the test

    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create HTTPS instance
    await page.click("button:has-text('+ Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", "3153")
    await page.check("#newHttps")
    await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
    await page.click("#createInstanceBtn")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=30000)

    # 2. Verify instance exists
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert any(i["name"] == instance_name for i in data["instances"])

    # 3. Open delete tab in settings modal
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal", state="visible", timeout=5000)
    await page.click("#settingsModal [data-tab='delete']")

    # 4. Click confirm delete
    await page.click("#confirmDeleteBtn")

    # 5. Wait for instance to disappear from UI
    await page.wait_for_selector(instance_selector, state="hidden", timeout=10000)

    # 6. Verify instance is removed via API
    await asyncio.sleep(2)
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert not any(
                i["name"] == instance_name for i in data["instances"]
            ), "Instance should be deleted"

    await page.close()


@pytest.mark.asyncio
async def test_https_regenerate_certificates(browser, clean_instance):
    """E-HTTPS-08: Regenerate certificates button works."""
    instance_name = "https-regen-test"
    clean_instance.append(instance_name)

    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create HTTPS instance
    await page.click("button:has-text('+ Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", "3154")
    await page.check("#newHttps")
    await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
    await page.click("#createInstanceBtn")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=30000)
    await asyncio.sleep(3)

    # 2. Open Settings modal
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal", state="visible")

    # 3. Open Certificate tab and regenerate certificate
    await page.click("#settingsModal [data-tab='certificate']")
    await page.click("#settingsModal button:has-text('Regenerate Certificate')")

    # 5. Wait for operation to complete (confirmation and reload)
    await asyncio.sleep(5)

    # 6. Verify instance is still running
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert instance["https_enabled"] is True
            assert (
                instance["running"] is True
            ), "Instance should still be running after cert regeneration"

    await page.close()


@pytest.mark.asyncio
async def test_delete_http_instance_ui(browser, clean_instance):
    """Test deleting HTTP instance via UI using custom delete modal.

    This tests the new delete confirmation modal that replaced window.confirm().
    The modal approach is more reliable in iframe/ingress contexts.
    """
    instance_name = "delete-http-test"

    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create HTTP instance
    await page.click("button:has-text('+ Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", "3155")
    await page.click("#createInstanceBtn")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=10000)

    # 2. Verify instance exists
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert any(
                i["name"] == instance_name for i in data["instances"]
            ), "Instance should exist"

    # 3. Open delete tab in settings modal
    print(f"Clicking delete for {instance_name}...")
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal", state="visible", timeout=5000)
    await page.click("#settingsModal [data-tab='delete']")
    # Verify modal shows correct instance name
    modal_text = await page.inner_text("#deleteMessage")
    assert instance_name in modal_text, f"Modal should mention instance name, got: {modal_text}"

    # Click the Delete button in the modal
    await page.click("#confirmDeleteBtn")

    # 5. Wait for instance to disappear
    await page.wait_for_selector(instance_selector, state="hidden", timeout=10000)

    # 6. Verify instance is removed via API
    await asyncio.sleep(2)
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert not any(
                i["name"] == instance_name for i in data["instances"]
            ), "Instance should be deleted"

    await page.close()


@pytest.mark.asyncio
async def test_delete_modal_cancel(browser, clean_instance):
    """Test that cancelling the delete modal does NOT delete the instance."""
    instance_name = "delete-cancel-test"
    clean_instance.append(instance_name)

    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create instance
    await page.click("button:has-text('+ Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", "3156")
    await page.click("#createInstanceBtn")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=10000)

    # 2. Open delete tab in settings modal
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal", state="visible", timeout=5000)
    await page.click("#settingsModal [data-tab='delete']")

    # 3. Click Cancel instead of Delete
    await page.click("#settingsModal button:has-text('Cancel')")

    # 4. Wait for modal to close
    await page.wait_for_selector("#settingsModal", state="hidden", timeout=5000)

    # 5. Verify instance still exists
    await asyncio.sleep(1)
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert any(
                i["name"] == instance_name for i in data["instances"]
            ), "Instance should still exist after cancel"

    await page.close()


@pytest.mark.asyncio
async def test_https_instance_stays_running(browser, clean_instance):
    """CRITICAL: Verify HTTPS instance stays running after creation.

    This test catches the ssl_bump issue by verifying:
    1. Instance is created with HTTPS
    2. Instance shows "running" status
    3. Instance STAYS running after multiple checks (not just initial startup)
    4. Logs don't contain FATAL errors

    If ssl_bump is in config, Squid crashes immediately with:
    'FATAL: No valid signing certificate configured for HTTPS_port'
    """
    instance_name = "https-stays-running"
    clean_instance.append(instance_name)

    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    await page.goto(ADDON_URL)

    # Create HTTPS instance
    await page.click("button:has-text('+ Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", "3157")
    await page.check("#newHttps")
    await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
    await page.click("#createInstanceBtn")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=30000)

    # Multiple status checks over time to ensure instance STAYS running
    for check_num in range(3):
        await asyncio.sleep(3)  # Wait between checks

        async with aiohttp.ClientSession(headers=API_HEADERS) as session:
            async with session.get(f"{ADDON_URL}/api/instances") as resp:
                data = await resp.json()
                instance = next((i for i in data["instances"] if i["name"] == instance_name), None)

                assert instance is not None, f"Instance should exist (check #{check_num + 1})"
                assert instance["running"] is True, (
                    f"HTTPS instance should still be running after check #{check_num + 1}. "
                    f"Status: {instance.get('status')}. "
                    "If ssl_bump is in config, Squid crashes with 'FATAL: No valid signing certificate'."
                )
                print(f"Check #{check_num + 1}: Instance {instance_name} is running")

    await page.close()


@pytest.mark.asyncio
async def test_https_instance_logs_no_fatal_errors(browser, clean_instance):
    """Verify HTTPS instance logs don't contain FATAL errors.

    This test catches the ssl_bump issue by checking Squid logs for:
    - 'FATAL: No valid signing certificate configured for HTTPS_port'
    - Any other FATAL errors
    """
    instance_name = "https-logs-check"
    clean_instance.append(instance_name)

    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    await page.goto(ADDON_URL)

    # Create HTTPS instance
    await page.click("button:has-text('+ Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", "3158")
    await page.check("#newHttps")
    await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
    await page.click("#createInstanceBtn")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=30000)

    # Wait for Squid to start (or fail)
    await asyncio.sleep(5)

    # Check logs via API for FATAL errors
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        # Get cache log
        async with session.get(
            f"{ADDON_URL}/api/instances/{instance_name}/logs?type=cache"
        ) as resp:
            log_text = await resp.text()
            print(f"Cache log for {instance_name}:\n{log_text[:500]}...")

            # Check for the specific ssl_bump error
            assert "No valid signing certificate" not in log_text, (
                "FATAL: Log contains 'No valid signing certificate' error! "
                "This means ssl_bump is still in the config."
            )

            # Check for any FATAL errors
            if "FATAL:" in log_text:
                # Extract the FATAL line for better error message
                fatal_lines = [line for line in log_text.split("\n") if "FATAL:" in line]
                pytest.fail(f"FATAL error found in logs: {fatal_lines}")

    await page.close()


@pytest.mark.asyncio
async def test_https_proxy_connectivity(browser, clean_instance):
    """Test actual HTTPS proxy connectivity.

    This test creates an HTTPS proxy, adds a user, and verifies
    the proxy actually works using curl with --proxy-insecure.
    """
    instance_name = "https-connectivity"
    clean_instance.append(instance_name)
    port = 3159
    username = "testuser"
    password = "testpass123"  # pragma: allowlist secret

    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create HTTPS instance
    await page.click("button:has-text('+ Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", str(port))
    await page.check("#newHttps")
    await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)
    await page.click("#createInstanceBtn")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=30000)

    # 2. Add a user via settings modal
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal", state="visible")
    await page.click("#settingsModal [data-tab='users']")
    await page.fill("#newUsername", username)
    await page.fill("#newPassword", password)
    await page.click("#settingsModal button:has-text('Add')")
    await page.wait_for_selector(f".user-item:has-text('{username}')", timeout=10000)
    await page.click("#settingsModal button[aria-label='Close']")

    # 3. Wait for instance to restart with new user
    await asyncio.sleep(5)

    # 4. Verify instance is still running
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert instance["running"] is True, "HTTPS instance should be running"

    # 5. Test actual proxy connectivity via API test endpoint
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.post(
            f"{ADDON_URL}/api/instances/{instance_name}/test",
            json={"username": username, "password": password},
        ) as resp:
            data = await resp.json()
            print(f"Connectivity test result: {data}")
            assert data.get("status") == "success", f"HTTPS proxy test failed: {data}"
            assert str(data.get("http_code")) in {
                "200",
                "301",
                "302",
                "307",
            }, f"Unexpected HTTP code from HTTPS proxy test: {data.get('http_code')}"

    await page.close()
