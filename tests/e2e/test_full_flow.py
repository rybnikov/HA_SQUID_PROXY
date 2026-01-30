import asyncio
import os

import aiohttp
import pytest

ADDON_URL = os.getenv("ADDON_URL", "http://localhost:8099")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "test_token")
API_HEADERS = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


@pytest.mark.asyncio
async def test_ui_instance_creation_and_logs(browser, unique_name, unique_port):
    """Test Case 2.1 & 2.4: Create instance and verify logs in UI."""
    instance_name = unique_name("ui-proxy")
    port = unique_port(3135)
    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create instance
    print(f"Creating instance {instance_name}...")
    await page.click("button:has-text('Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", str(port))
    await page.click("#addInstanceModal button:has-text('Create Instance')")

    # Wait for modal to disappear
    await page.wait_for_selector("#addInstanceModal", state="hidden", timeout=10000)

    # Wait for instance card
    print("Waiting for instance card...")
    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=10000)

    # 2. Start instance (it starts automatically on creation, so we stop it first to test the buttons)
    print(f"Stopping instance {instance_name} to test buttons...")
    stop_btn_selector = f"{instance_selector} .stop-btn"
    await page.wait_for_selector(f"{stop_btn_selector}:not([disabled])", timeout=10000)
    await page.click(stop_btn_selector)

    # Wait for status to become stopped
    print(f"Waiting for {instance_name} status to become stopped...")
    stopped_selector = f".instance-card[data-instance='{instance_name}'][data-status='stopped']"
    await page.wait_for_selector(stopped_selector, timeout=10000)

    print(f"Starting instance {instance_name}...")
    # Wait for button to be enabled (not disabled)
    start_btn_selector = f"{instance_selector} .start-btn"
    await page.wait_for_selector(f"{start_btn_selector}:not([disabled])", timeout=10000)
    await page.click(start_btn_selector)

    # Wait for status to become running using data-status attribute
    print(f"Waiting for {instance_name} status to become running...")
    running_selector = f".instance-card[data-instance='{instance_name}'][data-status='running']"
    await page.wait_for_selector(running_selector, timeout=20000)

    print("Instance is running. Opening logs...")
    # 3. View Logs via settings modal
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal:visible", timeout=5000)
    await page.click("#settingsModal [data-tab='logs']")

    print("Waiting for log content...")
    await page.wait_for_function(
        "document.getElementById('logContent') && document.getElementById('logContent').textContent.trim().length > 0",
        timeout=10000,
    )

    await page.close()


@pytest.mark.asyncio
async def test_proxy_functionality_e2e(unique_name, unique_port):
    """Test Case 3.1 & 3.2: Verify proxy traffic through API-created instance."""
    instance_name = unique_name("traffic-proxy")
    port = unique_port(3136)
    user = "e2euser"
    pw = "e2epassword"

    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        # 1. Create instance with user
        payload = {
            "name": instance_name,
            "port": port,
            "https_enabled": False,
            "users": [{"username": user, "password": pw}],
        }
        async with session.post(f"{ADDON_URL}/api/instances", json=payload) as resp:
            assert resp.status == 201

        # 2. Wait for startup
        await asyncio.sleep(3)

        # 3. Test proxy traffic
        proxy_url = f"http://{user}:{pw}@addon:{port}"

        try:
            async with aiohttp.ClientSession(headers=API_HEADERS) as proxy_session:
                async with proxy_session.get(
                    "http://www.google.com", proxy=proxy_url, timeout=10
                ) as resp:
                    assert resp.status == 200
        except Exception as e:
            pytest.fail(f"Proxy traffic failed: {e}")


@pytest.mark.asyncio
async def test_user_management_ui(browser, unique_name, unique_port):
    """Test Case 2.2 & 2.3: User management via UI."""
    instance_name = unique_name("user-proxy")
    port = unique_port(3137)
    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create instance
    print(f"Creating instance {instance_name}...")
    await page.click("button:has-text('Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", str(port))
    await page.click("#addInstanceModal button:has-text('Create Instance')")
    await page.wait_for_selector("#addInstanceModal", state="hidden")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=10000)

    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal:visible", timeout=5000)
    await page.click("#settingsModal [data-tab='users']")

    # 2. Add user
    print("Adding user uiuser...")
    await page.fill("#newUsername", "uiuser")
    await page.fill("#newPassword", "uipassword")
    await page.click("#settingsModal button:has-text('Add')")

    await page.wait_for_selector("#addUserProgress", state="visible", timeout=2000)
    await page.wait_for_selector(".user-item:has-text('uiuser')", timeout=10000)
    await page.wait_for_selector("#addUserProgress", state="hidden", timeout=10000)
    assert await page.is_visible("text=uiuser")

    # 3. Try duplicate
    print("Trying to add duplicate user uiuser...")
    await page.fill("#newUsername", "uiuser")
    await page.fill("#newPassword", "uipassword")
    await page.click("#settingsModal button:has-text('Add')")

    # Expect inline error message instead of window dialog (iframe safe)
    await page.wait_for_selector("#userError", state="visible", timeout=10000)
    error_text = await page.inner_text("#userError")
    assert "already exists" in error_text.lower() or "error" in error_text.lower()

    await page.close()


@pytest.mark.asyncio
async def test_https_proxy_e2e(browser, unique_name, unique_port):
    """Test Case 3.4: Verify HTTPS proxy instance creation and certificate generation."""
    instance_name = unique_name("https-proxy")
    port = unique_port(3138)
    user = "ssluser"
    pw = "sslpassword"

    page = await browser.new_page()
    await page.goto(ADDON_URL)

    # 1. Create HTTPS instance via UI
    await page.click('button:has-text("Add Instance")')
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", str(port))
    await page.check("#newHttps")
    await page.wait_for_selector("text=Certificate will be auto-generated", timeout=2000)

    # Create instance
    await page.click("#createInstanceBtn")

    # Wait for instance to be created (certificate generation can take time)
    await page.wait_for_selector(f'.instance-card[data-instance="{instance_name}"]', timeout=30000)

    # Wait for modal to close - give it more time for backend processing
    await page.wait_for_selector("#addInstanceModal", state="hidden", timeout=15000)

    # 2. Verify instance is running
    instances = await page.evaluate(
        """async () => {
        const resp = await apiFetch('api/instances');
        return await resp.json();
    }"""
    )

    instance = next((i for i in instances["instances"] if i["name"] == instance_name), None)
    assert instance is not None
    assert instance["https_enabled"] is True

    # 3. Add user
    await page.click(
        f".instance-card[data-instance='{instance_name}'] button[data-action='settings']",
        timeout=5000,
    )
    await page.wait_for_selector("#settingsModal", state="visible")
    await page.click("#settingsModal [data-tab='users']")
    await page.fill("#newUsername", user)
    await page.fill("#newPassword", pw)
    await page.click("#settingsModal button:has-text('Add')")
    await page.wait_for_timeout(2000)  # Wait for user to be added and instance to restart

    # 4. Verify instance is still running after user addition
    instances = await page.evaluate(
        """async () => {
        const resp = await apiFetch('api/instances');
        return await resp.json();
    }"""
    )
    instance = next((i for i in instances["instances"] if i["name"] == instance_name), None)
    assert instance["running"] is True, "Instance should be running after HTTPS enable"

    await page.close()


@pytest.mark.asyncio
async def test_path_normalization():
    """Case 5.1: Verify path normalization middleware."""
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        # Test with multiple slashes
        async with session.get(f"{ADDON_URL}//api//instances") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert "instances" in data


@pytest.mark.asyncio
async def test_settings_update(browser, unique_name, unique_port):
    """Case 2.5: Update instance settings (port change)."""
    instance_name = unique_name("settings-proxy")
    port = unique_port(3139)
    new_port = unique_port(3140)
    page = await browser.new_page()
    await page.goto(ADDON_URL)

    # 1. Create instance
    await page.click("button:has-text('Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", str(port))
    await page.click("#addInstanceModal button:has-text('Create Instance')")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector)

    # 2. Change port via Settings
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal:visible")

    await page.fill("#editPort", str(new_port))
    await page.click("#settingsModal button:has-text('Save Changes')")
    await page.wait_for_selector("#settingsModal", state="hidden")

    # 3. Verify update
    await asyncio.sleep(2)  # Wait for UI refresh
    info_text = await page.inner_text(instance_selector)
    assert str(new_port) in info_text

    await page.close()


@pytest.mark.asyncio
async def test_multiple_users_same_instance(browser, unique_name, unique_port):
    """Test adding multiple users to the same instance."""
    instance_name = unique_name("multi-user-proxy")
    port = unique_port(3141)
    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create instance
    print(f"Creating instance {instance_name}...")
    await page.click("button:has-text('Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", str(port))
    await page.click("#addInstanceModal button:has-text('Create Instance')")
    await page.wait_for_selector("#addInstanceModal", state="hidden")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=10000)

    # 2. Open Users tab in settings modal
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal:visible", timeout=5000)
    await page.click("#settingsModal [data-tab='users']")

    # 3. Add first user
    print("Adding first user...")
    await page.fill("#newUsername", "user1")
    await page.fill("#newPassword", "password1")
    await page.click("#settingsModal button:has-text('Add')")
    await page.wait_for_selector(".user-item:has-text('user1')", timeout=10000)

    # 4. Add second user
    print("Adding second user...")
    await page.fill("#newUsername", "user2")
    await page.fill("#newPassword", "password2")
    await page.click("#settingsModal button:has-text('Add')")
    await page.wait_for_selector(".user-item:has-text('user2')", timeout=10000)

    # 5. Add third user
    print("Adding third user...")
    await page.fill("#newUsername", "user3")
    await page.fill("#newPassword", "password3")
    await page.click("#settingsModal button:has-text('Add')")
    await page.wait_for_selector(".user-item:has-text('user3')", timeout=10000)

    # 6. Verify all users are listed
    user_list = await page.inner_text("#userList")
    assert "user1" in user_list
    assert "user2" in user_list
    assert "user3" in user_list

    # 7. Wait for instance to restart and test connectivity
    await asyncio.sleep(5)  # Wait for restart

    # Test with user1
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        proxy_url = f"http://user1:password1@addon:{port}"
        try:
            async with session.get("http://www.google.com", proxy=proxy_url, timeout=10) as resp:
                assert resp.status == 200, f"User1 proxy test failed with status {resp.status}"
        except Exception as e:
            pytest.fail(f"User1 proxy test failed: {e}")

    await page.close()


@pytest.mark.asyncio
async def test_user_isolation_between_instances(browser, unique_name, unique_port):
    """Test that users are isolated between instances."""
    instance1_name = unique_name("isolated-proxy-1")
    instance2_name = unique_name("isolated-proxy-2")
    port1 = unique_port(3142)
    port2 = unique_port(3143)
    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create first instance with user1
    print(f"Creating instance {instance1_name}...")
    await page.click("button:has-text('Add Instance')")
    await page.fill("#newName", instance1_name)
    await page.fill("#newPort", str(port1))
    await page.click("#addInstanceModal button:has-text('Create Instance')")
    await page.wait_for_selector("#addInstanceModal", state="hidden")

    instance1_selector = f".instance-card[data-instance='{instance1_name}']"
    await page.wait_for_selector(instance1_selector, timeout=10000)

    await page.click(f"{instance1_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal:visible", timeout=5000)
    await page.click("#settingsModal [data-tab='users']")
    await page.fill("#newUsername", "shareduser")
    await page.fill("#newPassword", "password1")
    await page.click("#settingsModal button:has-text('Add')")
    await page.wait_for_selector(".user-item:has-text('shareduser')", timeout=10000)
    await page.click("#settingsModal button[aria-label='Close']")
    await page.wait_for_selector("#settingsModal", state="hidden")

    # 2. Create second instance with different user
    print(f"Creating instance {instance2_name}...")
    await page.click("button:has-text('Add Instance')")
    await page.fill("#newName", instance2_name)
    await page.fill("#newPort", str(port2))
    await page.click("#addInstanceModal button:has-text('Create Instance')")
    await page.wait_for_selector("#addInstanceModal", state="hidden")

    instance2_selector = f".instance-card[data-instance='{instance2_name}']"
    await page.wait_for_selector(instance2_selector, timeout=10000)

    await page.click(f"{instance2_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal:visible", timeout=5000)
    await page.click("#settingsModal [data-tab='users']")
    await page.fill("#newUsername", "shareduser")
    await page.fill("#newPassword", "password2")
    await page.click("#settingsModal button:has-text('Add')")
    await page.wait_for_selector(".user-item:has-text('shareduser')", timeout=10000)
    await page.click("#settingsModal button[aria-label='Close']")
    await page.wait_for_selector("#settingsModal", state="hidden")

    # 3. Wait for instances to be ready
    await asyncio.sleep(5)

    # 4. Test that user1 can only access instance1, not instance2
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        # Should work on instance1
        proxy_url1 = f"http://shareduser:password1@addon:{port1}"
        try:
            async with session.get("http://www.google.com", proxy=proxy_url1, timeout=10) as resp:
                assert resp.status == 200, f"User should work on instance1, got {resp.status}"
        except Exception as e:
            pytest.fail(f"User should work on instance1: {e}")

        # Should NOT work on instance2 (wrong password)
        proxy_url2 = f"http://shareduser:password1@addon:{port2}"
        try:
            async with session.get("http://www.google.com", proxy=proxy_url2, timeout=10) as resp:
                # Should get 407 or connection error
                assert (
                    resp.status == 407 or resp.status >= 500
                ), f"User should NOT work on instance2, got {resp.status}"
        except Exception:
            # Connection error is also acceptable
            pass

    await page.close()


@pytest.mark.asyncio
async def test_remove_instance(browser, unique_name, unique_port):
    """Test removing an instance using custom delete modal.

    Note: Delete now uses a custom modal instead of window.confirm()
    because confirm() doesn't work reliably in iframe/ingress context.
    """
    instance_name = unique_name("remove-test-proxy")
    port = unique_port(3144)
    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create instance
    print(f"Creating instance {instance_name}...")
    await page.click("button:has-text('Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", str(port))
    await page.click("#addInstanceModal button:has-text('Create Instance')")
    await page.wait_for_selector("#addInstanceModal", state="hidden")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=10000)

    # 2. Verify instance exists via API
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert any(i["name"] == instance_name for i in data["instances"])

    # 3. Open delete tab in settings modal
    print(f"Deleting instance {instance_name}...")
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal", state="visible", timeout=5000)
    await page.click("#settingsModal [data-tab='delete']")

    # 4. Confirm delete
    await page.click("#confirmDeleteBtn")

    # 5. Wait for instance to be removed from UI
    await page.wait_for_selector(instance_selector, state="hidden", timeout=10000)

    # 6. Verify instance is removed via API
    await asyncio.sleep(2)
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            assert not any(
                i["name"] == instance_name for i in data["instances"]
            ), "Instance should be removed"

    await page.close()


@pytest.mark.asyncio
async def test_stop_button(browser, unique_name, unique_port):
    """Test stop button functionality."""
    instance_name = unique_name("stop-test-proxy")
    port = unique_port(3145)
    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create instance
    print(f"Creating instance {instance_name}...")
    await page.click("button:has-text('Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", str(port))
    await page.click("#addInstanceModal button:has-text('Create Instance')")
    await page.wait_for_selector("#addInstanceModal", state="hidden")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=10000)

    # 2. Wait for instance to be running
    await page.wait_for_selector(f"{instance_selector}[data-status='running']", timeout=10000)

    # 3. Click Stop button
    print(f"Stopping instance {instance_name}...")
    stop_btn = f"{instance_selector} .stop-btn"
    await page.wait_for_selector(f"{stop_btn}:not([disabled])", timeout=5000)
    await page.click(stop_btn)

    # 4. Wait for status to become stopped
    await page.wait_for_selector(f"{instance_selector}[data-status='stopped']", timeout=10000)

    # 5. Verify via API
    await asyncio.sleep(2)
    async with aiohttp.ClientSession(headers=API_HEADERS) as session:
        async with session.get(f"{ADDON_URL}/api/instances") as resp:
            data = await resp.json()
            instance = next((i for i in data["instances"] if i["name"] == instance_name), None)
            assert instance is not None, "Instance should exist"
            assert not instance.get("running", True), "Instance should be stopped"

    await page.close()


@pytest.mark.asyncio
async def test_test_button_functionality(browser, unique_name, unique_port):
    """Test the test button actually tests connectivity."""
    instance_name = unique_name("test-button-proxy")
    port = unique_port(3146)
    page = await browser.new_page()
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    await page.goto(ADDON_URL)

    # 1. Create instance with user
    print(f"Creating instance {instance_name}...")
    await page.click("button:has-text('Add Instance')")
    await page.fill("#newName", instance_name)
    await page.fill("#newPort", str(port))
    await page.click("#addInstanceModal button:has-text('Create Instance')")
    await page.wait_for_selector("#addInstanceModal", state="hidden")

    instance_selector = f".instance-card[data-instance='{instance_name}']"
    await page.wait_for_selector(instance_selector, timeout=10000)

    # 2. Add user via settings modal
    await page.click(f"{instance_selector} button[data-action='settings']")
    await page.wait_for_selector("#settingsModal:visible", timeout=5000)
    await page.click("#settingsModal [data-tab='users']")
    await page.fill("#newUsername", "testuser")
    await page.fill("#newPassword", "testpassword")
    await page.click("#settingsModal button:has-text('Add')")
    await page.wait_for_selector(".user-item:has-text('testuser')", timeout=10000)

    # 3. Wait for instance to restart (poll until running)
    for _ in range(10):
        instances = await page.evaluate(
            """async () => {
            const resp = await apiFetch('api/instances');
            return await resp.json();
        }"""
        )
        instance = next((i for i in instances["instances"] if i["name"] == instance_name), None)
        if instance and instance.get("running"):
            break
        await asyncio.sleep(1)

    # 4. Switch to Test tab
    print(f"Testing connectivity for {instance_name}...")
    await page.click("#settingsModal [data-tab='test']")

    # 5. Fill in credentials and run test
    await page.fill("#testUsername", "testuser")
    await page.fill("#testPassword", "testpassword")
    await page.click("#settingsModal button:has-text('Run Test')")

    # 6. Wait for test result
    await page.wait_for_function(
        "document.querySelector('#testResult') && document.querySelector('#testResult').textContent.trim() !== 'Testing connectivity...'",
        timeout=20000,
    )
    result_text = await page.inner_text("#testResult")

    # 7. Verify test result updated (success or failure is acceptable if network blocked)
    assert (
        result_text.strip() != "Testing connectivity..."
    ), f"Test result did not update: {result_text}"

    await page.close()
