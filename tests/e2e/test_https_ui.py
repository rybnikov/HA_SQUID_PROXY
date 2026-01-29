"""E2E tests for HTTPS functionality via UI.

These tests verify that HTTPS can be enabled, configured, and used
through the web UI, matching the test plan in HTTPS_TEST_PLAN.md.
"""
import asyncio
import pytest
import aiohttp

# Test addon URL - configured in conftest.py
ADDON_URL = "http://addon:8099"


@pytest.fixture
async def clean_instance(browser):
    """Clean up instance after test."""
    instances_to_clean = []
    yield instances_to_clean
    
    # Cleanup after test
    async with aiohttp.ClientSession() as session:
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
    
    # 4. Verify certificate settings appear
    await page.wait_for_selector("#newCertSettings", state="visible", timeout=2000)
    
    # 5. Fill certificate parameters
    await page.fill("#newCertCN", "test-https-proxy")
    await page.fill("#newCertValidity", "365")
    await page.select_option("#newCertKeySize", "2048")
    
    # 6. Create instance
    await page.click("#createInstanceBtn")
    
    # 7. Wait for modal to close and instance to appear
    await page.wait_for_selector("#addInstanceModal", state="hidden", timeout=30000)
    await page.wait_for_selector(f".instance-card[data-instance='{instance_name}']", timeout=30000)
    
    # 8. Verify instance is created with HTTPS
    async with aiohttp.ClientSession() as session:
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
    
    # Certificate settings should be hidden initially
    cert_settings = await page.query_selector("#newCertSettings")
    is_hidden = await cert_settings.is_hidden()
    assert is_hidden, "Certificate settings should be hidden initially"
    
    # Check HTTPS checkbox
    await page.check("#newHttps")
    
    # Certificate settings should be visible now
    await page.wait_for_selector("#newCertSettings", state="visible", timeout=2000)
    is_visible = await page.is_visible("#newCertSettings")
    assert is_visible, "Certificate settings should be visible when HTTPS is checked"
    
    # Uncheck HTTPS
    await page.uncheck("#newHttps")
    
    # Certificate settings should be hidden again
    await page.wait_for_selector("#newCertSettings", state="hidden", timeout=2000)
    
    await page.close()


@pytest.mark.asyncio
async def test_https_instance_starts_from_ui(browser, clean_instance):
    """E-HTTPS-05: HTTPS instance starts from UI and shows Running status."""
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
    await page.wait_for_selector("#newCertSettings", state="visible")
    await page.click("#createInstanceBtn")
    
    # Wait for instance to be created and started
    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=30000)
    
    # Wait for status to show Running
    await asyncio.sleep(5)  # Give Squid time to start
    
    # Verify via API
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            # Instance should be running (certificate generation and Squid start succeeded)
            # Note: If HTTPS is still broken, this will fail - that's the purpose of this test
            assert instance["running"] is True, f"HTTPS instance should be running. Status: {instance.get('status')}"
    
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
    await page.click(f"{instance_selector} button:has-text('Settings')")
    await page.wait_for_selector("#settingsModal", state="visible")
    
    # 4. Enable HTTPS
    await page.check("#editHttps")
    await page.wait_for_selector("#editCertSettings", state="visible", timeout=2000)
    
    # 5. Save changes
    await page.click("#settingsModal button:has-text('Save Changes')")
    
    # 6. Wait for modal to close and instance to restart
    await page.wait_for_selector("#settingsModal", state="hidden", timeout=30000)
    await asyncio.sleep(5)  # Wait for restart with HTTPS
    
    # 7. Verify HTTPS is enabled via API
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert instance["https_enabled"] is True, "HTTPS should be enabled"
            assert instance["running"] is True, "Instance should still be running after HTTPS enable"
    
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
    await page.wait_for_selector("#newCertSettings", state="visible")
    await page.click("#createInstanceBtn")
    
    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=30000)
    
    # 2. Verify instance exists
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert any(i["name"] == instance_name for i in data["instances"])
    
    # 3. Click Delete button - this opens the custom delete modal
    await page.click(f"{instance_selector} button:has-text('Delete')")
    
    # 4. Wait for delete modal to appear and click confirm
    await page.wait_for_selector("#deleteModal", state="visible", timeout=5000)
    await page.click("#deleteModal button:has-text('Delete')")
    
    # 5. Wait for instance to disappear from UI
    await page.wait_for_selector(instance_selector, state="hidden", timeout=10000)
    
    # 6. Verify instance is removed via API
    await asyncio.sleep(2)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert not any(i["name"] == instance_name for i in data["instances"]), "Instance should be deleted"
    
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
    await page.wait_for_selector("#newCertSettings", state="visible")
    await page.click("#createInstanceBtn")
    
    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=30000)
    await asyncio.sleep(3)
    
    # 2. Open Settings modal
    await page.click(f"{instance_selector} button:has-text('Settings')")
    await page.wait_for_selector("#settingsModal", state="visible")
    
    # 3. Verify HTTPS is checked and cert actions are visible
    is_checked = await page.is_checked("#editHttps")
    assert is_checked, "HTTPS should be checked"
    
    # 4. Click Regenerate Certificates
    await page.click("#certActions button:has-text('Regenerate Certificates')")
    
    # 5. Wait for operation to complete (confirmation and reload)
    await asyncio.sleep(5)
    
    # 6. Verify instance is still running
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None
            assert instance["https_enabled"] is True
            assert instance["running"] is True, "Instance should still be running after cert regeneration"
    
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
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert any(i["name"] == instance_name for i in data["instances"]), "Instance should exist"
    
    # 3. Click Delete button - opens custom modal
    print(f"Clicking delete for {instance_name}...")
    await page.click(f"{instance_selector} button:has-text('Delete')")
    
    # 4. Wait for delete modal and confirm
    await page.wait_for_selector("#deleteModal", state="visible", timeout=5000)
    # Verify modal shows correct instance name
    modal_text = await page.inner_text("#deleteMessage")
    assert instance_name in modal_text, f"Modal should mention instance name, got: {modal_text}"
    
    # Click the Delete button in the modal
    await page.click("#deleteModal button:has-text('Delete')")
    
    # 5. Wait for instance to disappear
    await page.wait_for_selector(instance_selector, state="hidden", timeout=10000)
    
    # 6. Verify instance is removed via API
    await asyncio.sleep(2)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert not any(i["name"] == instance_name for i in data["instances"]), "Instance should be deleted"
    
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
    
    # 2. Click Delete button - opens modal
    await page.click(f"{instance_selector} button:has-text('Delete')")
    await page.wait_for_selector("#deleteModal", state="visible", timeout=5000)
    
    # 3. Click Cancel instead of Delete
    await page.click("#deleteModal button:has-text('Cancel')")
    
    # 4. Wait for modal to close
    await page.wait_for_selector("#deleteModal", state="hidden", timeout=5000)
    
    # 5. Verify instance still exists
    await asyncio.sleep(1)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert any(i["name"] == instance_name for i in data["instances"]), "Instance should still exist after cancel"
    
    await page.close()
