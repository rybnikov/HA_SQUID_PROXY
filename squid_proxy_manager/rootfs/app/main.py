#!/usr/bin/env python3
"""Main entry point for Squid Proxy Manager add-on."""
# Very early logging setup to catch any startup issues
import os
import sys

# Set up basic logging immediately, before any other imports
try:
    import logging

    LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # Force reconfiguration if logging was already set up
    )
    _EARLY_LOGGER = logging.getLogger(__name__)
    _EARLY_LOGGER.info("=" * 60)
    _EARLY_LOGGER.info("Python script started - initializing...")
    _EARLY_LOGGER.info("Python version: %s", sys.version)
    _EARLY_LOGGER.info("Python executable: %s", sys.executable)
    _EARLY_LOGGER.info("Working directory: %s", os.getcwd())
    _EARLY_LOGGER.info("=" * 60)
except Exception as e:
    print(f"CRITICAL: Failed to set up logging: {e}", file=sys.stderr)
    sys.exit(1)

# Now do other imports with error handling
try:
    import asyncio
    import json
    from pathlib import Path

    _EARLY_LOGGER.info("Core imports successful")
except Exception as e:
    _EARLY_LOGGER.critical("Failed to import core modules: %s", e, exc_info=True)
    sys.exit(1)

try:
    import aiohttp
    from aiohttp import web

    _EARLY_LOGGER.info("aiohttp imports successful")
except Exception as e:
    _EARLY_LOGGER.critical("Failed to import aiohttp: %s", e, exc_info=True)
    sys.exit(1)

# Add app directory to path
sys.path.insert(0, "/app")
_EARLY_LOGGER.info("Added /app to Python path")

try:
    from proxy_manager import ProxyInstanceManager

    _EARLY_LOGGER.info("proxy_manager import successful")
except Exception as e:
    _EARLY_LOGGER.critical("Failed to import proxy_manager: %s", e, exc_info=True)
    sys.exit(1)

# Now use the logger normally
_LOGGER = _EARLY_LOGGER
_LOGGER.info("All imports completed successfully")

# Paths
CONFIG_PATH = Path("/data/options.json")
HA_API_URL = os.getenv("SUPERVISOR", "http://supervisor")
HA_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")

# Manager will be initialized in main()
manager = None


# Middlewares
@web.middleware
async def normalize_path_middleware(request, handler):
    """Normalize multiple slashes in path for ingress compatibility."""
    import re

    original_path = request.path
    normalized_path = re.sub(r"/+", "/", original_path)

    if normalized_path != original_path:
        _LOGGER.debug("Normalizing path: %s -> %s", original_path, normalized_path)

        # If the original request didn't match any route (handler is 404)
        # but the normalized path DOES match a route, we should use that instead.
        # This is common with ingress adding extra slashes.
        try:
            # Re-resolve the path
            cloned_request = request.clone(rel_url=request.rel_url.with_path(normalized_path))
            match_info = await request.app.router.resolve(cloned_request)

            if match_info.http_exception is None:
                # We found a better match!
                # IMPORTANT: We must use the match_info handler and ensure the request
                # passed to it has the correct match_info attached.
                # In aiohttp, request.match_info is a property that accesses _match_info.
                # We need to set it on the cloned request.
                # Using setattr because it's technically a private attribute.
                cloned_request._match_info = match_info
                return await match_info.handler(cloned_request)
        except Exception:
            # Fallback to original handler if anything goes wrong
            pass

        # If we didn't find a better match, but it's just the root, handle it
        if normalized_path == "/":
            return await root_handler(request)

    return await handler(request)


@web.middleware
async def logging_middleware(request, handler):
    """Log requests and responses with status-based levels."""
    # Log all requests at DEBUG, but log errors at INFO/ERROR
    _LOGGER.debug("Request: %s %s from %s", request.method, request.path_qs, request.remote)
    try:
        response = await handler(request)
        if response.status >= 400:
            _LOGGER.info("Response: %s %s -> %d", request.method, request.path_qs, response.status)
        else:
            _LOGGER.debug("Response: %s %s -> %d", request.method, request.path_qs, response.status)
        return response
    except web.HTTPException as ex:
        # Handle known HTTP exceptions (like 404) without logging a full traceback
        if ex.status >= 400:
            _LOGGER.info("Response: %s %s -> %d", request.method, request.path_qs, ex.status)
        raise
    except Exception as ex:
        _LOGGER.error(
            "Unhandled exception in handler for %s %s: %s",
            request.method,
            request.path_qs,
            ex,
            exc_info=True,
        )
        raise


async def get_config():
    """Load add-on configuration."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def get_ingress_port():
    """Get ingress port - using fixed port 8099.

    Using a fixed port (8099) configured in config.yaml for reliability.
    Dynamic port discovery with ingress_port: 0 proved unreliable.
    """
    # Use fixed port 8099 as configured in config.yaml
    port = 8099
    _LOGGER.info("Using fixed ingress port: %d (from config.yaml)", port)
    return port


async def root_handler(request):
    """Root endpoint for ingress - serves web UI or JSON."""
    _LOGGER.debug("Root handler called from %s", request.remote)

    # Check if client wants HTML (web UI)
    accept_header = request.headers.get("Accept", "")
    if "text/html" in accept_header:
        return await web_ui_handler(request)

    # Return JSON for API clients
    response_data = {
        "status": "ok",
        "service": "squid_proxy_manager",
        "version": "1.1.15",
        "api": "/api",
        "manager_initialized": manager is not None,
    }
    _LOGGER.info("Root endpoint accessed - manager initialized: %s", manager is not None)
    return web.json_response(response_data)


async def web_ui_handler(request):
    """Serve web UI HTML page."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Squid Proxy Manager</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        h1 {
            color: #4a9eff;
        }
        .status {
            padding: 10px;
            border-radius: 5px;
            margin: 20px 0;
            background: #2a2a2a;
        }
        .status.ok { border-left: 4px solid #4caf50; }
        .status.error { border-left: 4px solid #f44336; }
        .instances {
            margin-top: 30px;
        }
        .instance-card {
            background: #2a2a2a;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #4a9eff;
        }
        .instance-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }
        .instance-name {
            font-size: 1.2em;
            font-weight: bold;
            color: #4a9eff;
        }
        .instance-info {
            font-size: 0.9em;
            color: #b0b0b0;
            margin-bottom: 15px;
        }
        .btn {
            background: #4a9eff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px 5px 5px 0;
            font-size: 0.9em;
            transition: background 0.2s;
        }
        .btn:hover { background: #357abd; }
        .btn.secondary { background: #555; }
        .btn.secondary:hover { background: #666; }
        .btn.danger { background: #f44336; }
        .btn.danger:hover { background: #d32f2f; }
        .btn.success { background: #4caf50; }
        .btn.success:hover { background: #388e3c; }

        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 100;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
        }
        .modal-content {
            background-color: #2a2a2a;
            margin: 10% auto;
            padding: 20px;
            border-radius: 8px;
            width: 500px;
            max-width: 90%;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 1px solid #444;
            padding-bottom: 10px;
        }
        .modal-title {
            font-size: 1.5em;
            color: #4a9eff;
        }
        .close {
            color: #aaa;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover { color: #fff; }

        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], input[type="number"], input[type="password"] {
            width: 100%;
            padding: 10px;
            background: #1a1a1a;
            border: 1px solid #444;
            color: #e0e0e0;
            border-radius: 4px;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .user-list {
            margin-top: 20px;
        }
        .user-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: #1a1a1a;
            border-bottom: 1px solid #333;
        }

        .loading { text-align: center; padding: 20px; }
        .error { color: #f44336; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐙 Squid Proxy Manager</h1>
            <button class="btn success" onclick="openAddInstanceModal()">+ Add Instance</button>
        </div>
        <div id="status" class="status loading">Loading...</div>
        <div id="instances" class="instances"></div>
    </div>

    <!-- Add Instance Modal -->
    <div id="addInstanceModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title">Add New Instance</span>
                <span class="close" onclick="closeModal('addInstanceModal')">&times;</span>
            </div>
            <div class="form-group">
                <label for="newName">Instance Name</label>
                <input type="text" id="newName" placeholder="e.g. proxy1">
            </div>
            <div class="form-group">
                <label for="newPort">Port</label>
                <input type="number" id="newPort" value="3128">
            </div>
            <div class="form-group checkbox-group">
                <input type="checkbox" id="newHttps">
                <label for="newHttps">Enable HTTPS (SSL)</label>
            </div>
            <div style="text-align: right; margin-top: 20px;">
                <button class="btn secondary" onclick="closeModal('addInstanceModal')">Cancel</button>
                <button class="btn success" onclick="createInstance()">Create Instance</button>
            </div>
        </div>
    </div>

    <!-- User Management Modal -->
    <div id="userModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title" id="userModalTitle">Manage Users</span>
                <span class="close" onclick="closeModal('userModal')">&times;</span>
            </div>
            <input type="hidden" id="currentUserInstance">
            <div class="form-group">
                <label>Add User</label>
                <div style="display: flex; gap: 10px;">
                    <input type="text" id="newUsername" placeholder="Username" style="flex: 1;">
                    <input type="password" id="newPassword" placeholder="Password" style="flex: 1;">
                    <button class="btn success" onclick="addUser()">Add</button>
                </div>
            </div>
            <div id="userList" class="user-list">
                <!-- Users will be listed here -->
            </div>
            <div style="text-align: right; margin-top: 20px;">
                <button class="btn secondary" onclick="closeModal('userModal')">Close</button>
            </div>
        </div>
    </div>

    <!-- Settings Modal -->
    <div id="settingsModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title" id="settingsModalTitle">Instance Settings</span>
                <span class="close" onclick="closeModal('settingsModal')">&times;</span>
            </div>
            <input type="hidden" id="currentSettingsInstance">
            <div class="form-group">
                <label for="editPort">Port</label>
                <input type="number" id="editPort">
            </div>
            <div class="form-group checkbox-group">
                <input type="checkbox" id="editHttps">
                <label for="editHttps">Enable HTTPS (SSL)</label>
            </div>
            <div id="certActions" style="margin-top: 15px; display: none;">
                <button class="btn secondary" onclick="regenerateCerts()">Regenerate Certificates</button>
            </div>
            <div style="text-align: right; margin-top: 20px;">
                <button class="btn secondary" onclick="closeModal('settingsModal')">Cancel</button>
                <button class="btn success" onclick="updateSettings()">Save Changes</button>
            </div>
        </div>
    </div>

    <!-- Log Modal -->
    <div id="logModal" class="modal">
        <div class="modal-content" style="width: 800px; max-width: 95%;">
            <div class="modal-header">
                <span class="modal-title" id="logModalTitle">Instance Logs</span>
                <span class="close" onclick="closeModal('logModal')">&times;</span>
            </div>
            <input type="hidden" id="currentLogInstance">
            <div class="form-group">
                <button class="btn" onclick="loadLogs('cache')">Cache Log</button>
                <button class="btn" onclick="loadLogs('access')">Access Log</button>
            </div>
            <pre id="logContent" style="background: #1a1a1a; padding: 10px; border-radius: 4px; height: 400px; overflow-y: auto; font-size: 0.8em; white-space: pre-wrap; word-break: break-all;"></pre>
            <div style="text-align: right; margin-top: 20px;">
                <button class="btn secondary" onclick="closeModal('logModal')">Close</button>
            </div>
        </div>
    </div>

    <!-- Test Modal -->
    <div id="testModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title" id="testModalTitle">Test Connectivity</span>
                <span class="close" onclick="closeModal('testModal')">&times;</span>
            </div>
            <input type="hidden" id="currentTestInstance">
            <div class="form-group">
                <label for="testUsername">Username</label>
                <input type="text" id="testUsername" placeholder="Enter username">
            </div>
            <div class="form-group">
                <label for="testPassword">Password</label>
                <input type="password" id="testPassword" placeholder="Enter password">
            </div>
            <div id="testResult" style="margin-top: 15px; padding: 10px; border-radius: 4px; display: none;"></div>
            <div style="text-align: right; margin-top: 20px;">
                <button class="btn secondary" onclick="closeModal('testModal')">Close</button>
                <button class="btn success" onclick="runTest()">Run Test</button>
            </div>
        </div>
    </div>

    <script>
        // Store current instances to avoid unnecessary DOM updates
        let currentInstances = [];

        async function loadInstances() {
            try {
                const response = await fetch('api/instances');
                if (!response.ok) throw new Error('Failed to load instances');
                const data = await response.json();
                updateUI(data);
            } catch (error) {
                document.getElementById('status').innerHTML =
                    '<div class="error">Error: ' + error.message + '</div>';
            }
        }

        function updateUI(data) {
            const statusEl = document.getElementById('status');
            const instancesEl = document.getElementById('instances');

            if (data.error) {
                statusEl.className = 'status error';
                statusEl.innerHTML = '<div class="error">' + data.error + '</div>';
                return;
            }

            statusEl.className = 'status ok';
            statusEl.innerHTML = 'Service Status: <strong>Running</strong> | Instances: ' + data.count;

            instancesEl.innerHTML = data.instances.length > 0 ? '' : '<p>No instances configured.</p>';

            data.instances.forEach(instance => {
                const card = document.createElement('div');
                card.className = 'instance-card';
                card.setAttribute('data-instance', instance.name);
                card.setAttribute('data-status', instance.status);
                card.innerHTML = `
                    <div class="instance-header">
                        <div class="instance-name">${instance.name}</div>
                        <div>
                            <button class="btn success start-btn" onclick="startInstance('${instance.name}')" ${instance.running ? 'disabled' : ''}>Start</button>
                            <button class="btn secondary stop-btn" onclick="stopInstance('${instance.name}')" ${!instance.running ? 'disabled' : ''}>Stop</button>
                        </div>
                    </div>
                    <div class="instance-info">
                        Port: <strong>${instance.port}</strong> |
                        HTTPS: <strong>${instance.https_enabled ? 'Yes' : 'No'}</strong> |
                        Status: <strong class="status-text" style="color: ${instance.running ? '#4caf50' : '#f44336'}">${instance.status}</strong>
                    </div>
                    <div class="instance-actions">
                        <button class="btn" onclick="openUserModal('${instance.name}')">Users</button>
                        <button class="btn" onclick="openSettingsModal('${instance.name}', ${instance.port}, ${instance.https_enabled})">Settings</button>
                        <button class="btn secondary" onclick="openLogModal('${instance.name}')">Logs</button>
                        <button class="btn success" onclick="openTestModal('${instance.name}', ${instance.port}, ${instance.https_enabled})">Test</button>
                        <button class="btn danger" onclick="deleteInstance('${instance.name}')">Delete</button>
                    </div>
                `;
                instancesEl.appendChild(card);
            });
        }

        // Instance Operations
        async function createInstance() {
            const name = document.getElementById('newName').value;
            const port = parseInt(document.getElementById('newPort').value);
            const https_enabled = document.getElementById('newHttps').checked;

            if (!name) return alert('Name is required');

            try {
                const response = await fetch('api/instances', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, port, https_enabled })
                });
                const data = await response.json();
                if (data.error) throw new Error(data.error);
                closeModal('addInstanceModal');
                loadInstances();
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        async function startInstance(name) {
            const resp = await fetch(`api/instances/${name}/start`, { method: 'POST' });
            const data = await resp.json();
            if (data.error) alert('Error: ' + data.error);
            loadInstances();
        }

        async function stopInstance(name) {
            try {
                const resp = await fetch(`api/instances/${name}/stop`, { method: 'POST' });
                const data = await resp.json();
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                loadInstances();
            } catch (error) {
                alert('Error stopping instance: ' + error.message);
            }
        }

        async function deleteInstance(name) {
            if (!confirm(`Are you sure you want to delete instance "${name}"?`)) return;
            try {
                const resp = await fetch(`api/instances/${name}`, { method: 'DELETE' });
                const data = await resp.json();
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                loadInstances();
            } catch (error) {
                alert('Error deleting instance: ' + error.message);
            }
        }

        // User Operations
        async function openUserModal(name) {
            document.getElementById('userModalTitle').innerText = `Manage Users: ${name}`;
            document.getElementById('currentUserInstance').value = name;
            document.getElementById('userModal').style.display = 'block';
            loadUsers(name);
        }

        async function loadUsers(name) {
            const resp = await fetch(`api/instances/${name}/users`);
            const data = await resp.json();
            const listEl = document.getElementById('userList');
            listEl.innerHTML = data.users.length > 0 ? '' : '<p>No users configured.</p>';
            data.users.forEach(username => {
                const item = document.createElement('div');
                item.className = 'user-item';
                item.innerHTML = `
                    <span>${username}</span>
                    <button class="btn danger" onclick="removeUser('${username}')">Remove</button>
                `;
                listEl.appendChild(item);
            });
        }

        async function addUser() {
            const name = document.getElementById('currentUserInstance').value;
            const username = document.getElementById('newUsername').value;
            const password = document.getElementById('newPassword').value;

            if (!username || !password) {
                alert('Username and password are required');
                return;
            }

            try {
                const response = await fetch(`api/instances/${name}/users`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const data = await response.json();
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                document.getElementById('newUsername').value = '';
                document.getElementById('newPassword').value = '';
                loadUsers(name);
            } catch (error) {
                alert('Error adding user: ' + error.message);
            }
        }

        async function removeUser(username) {
            const name = document.getElementById('currentUserInstance').value;
            if (!confirm(`Remove user "${username}"?`)) return;
            try {
                const resp = await fetch(`api/instances/${name}/users/${username}`, { method: 'DELETE' });
                const data = await resp.json();
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                loadUsers(name);
            } catch (error) {
                alert('Error removing user: ' + error.message);
            }
        }

        // Settings Operations
        function openSettingsModal(name, port, https) {
            document.getElementById('settingsModalTitle').innerText = `Settings: ${name}`;
            document.getElementById('currentSettingsInstance').value = name;
            document.getElementById('editPort').value = port;
            document.getElementById('editHttps').checked = https;
            document.getElementById('certActions').style.display = https ? 'block' : 'none';
            document.getElementById('settingsModal').style.display = 'block';
        }

        async function regenerateCerts() {
            const name = document.getElementById('currentSettingsInstance').value;
            if (!confirm('Regenerate certificates? This will restart the instance.')) return;
            try {
                const response = await fetch(`api/instances/${name}/certs`, { method: 'POST' });
                const data = await response.json();
                if (data.error) throw new Error(data.error);
                alert('Certificates regenerated successfully');
                loadInstances();
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        async function updateSettings() {
            const name = document.getElementById('currentSettingsInstance').value;
            const port = parseInt(document.getElementById('editPort').value);
            const https_enabled = document.getElementById('editHttps').checked;

            try {
                const response = await fetch(`api/instances/${name}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ port, https_enabled })
                });
                const data = await response.json();
                if (data.error) throw new Error(data.error);
                closeModal('settingsModal');
                loadInstances();
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        // Log Operations
        async function openLogModal(name) {
            document.getElementById('logModalTitle').innerText = `Logs: ${name}`;
            document.getElementById('currentLogInstance').value = name;
            document.getElementById('logModal').style.display = 'block';
            document.getElementById('logContent').innerText = 'Loading logs...';
            loadLogs('cache');
        }

        async function loadLogs(type) {
            const name = document.getElementById('currentLogInstance').value;
            try {
                const response = await fetch(`api/instances/${name}/logs?type=${type}`);
                const text = await response.text();
                document.getElementById('logContent').innerText = text;
                // Scroll to bottom
                const pre = document.getElementById('logContent');
                pre.scrollTop = pre.scrollHeight;
            } catch (error) {
                document.getElementById('logContent').innerText = 'Error loading logs: ' + error.message;
            }
        }

        // Connectivity Test
        function openTestModal(name, port, https) {
            document.getElementById('testModalTitle').innerText = `Test Connectivity: ${name}`;
            document.getElementById('currentTestInstance').value = name;
            document.getElementById('testUsername').value = '';
            document.getElementById('testPassword').value = '';
            document.getElementById('testResult').style.display = 'none';
            document.getElementById('testResult').innerHTML = '';
            document.getElementById('testModal').style.display = 'block';
        }

        async function runTest() {
            const name = document.getElementById('currentTestInstance').value;
            const username = document.getElementById('testUsername').value;
            const password = document.getElementById('testPassword').value;
            const resultEl = document.getElementById('testResult');

            if (!username || !password) {
                alert('Username and password are required for testing');
                return;
            }

            resultEl.style.display = 'block';
            resultEl.innerHTML = 'Testing connectivity...';
            resultEl.style.background = '#2a2a2a';
            resultEl.style.color = '#e0e0e0';

            try {
                const response = await fetch(`api/instances/${name}/test`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    resultEl.style.background = '#4caf50';
                    resultEl.style.color = '#fff';
                    resultEl.innerHTML = `✓ Test successful! HTTP Code: ${data.http_code || 'N/A'}`;
                } else {
                    resultEl.style.background = '#f44336';
                    resultEl.style.color = '#fff';
                    resultEl.innerHTML = `✗ Test failed: ${data.error || data.message || 'Unknown error'}`;
                }
            } catch (error) {
                resultEl.style.background = '#f44336';
                resultEl.style.color = '#fff';
                resultEl.innerHTML = `✗ Error: ${error.message}`;
            }
        }

        // Modal Helpers
        function openAddInstanceModal() {
            document.getElementById('addInstanceModal').style.display = 'block';
        }

        function closeModal(id) {
            document.getElementById(id).style.display = 'none';
        }

        // Initial Load
        loadInstances();
        // Refresh every 2 seconds
        setInterval(loadInstances, 2000);

        // Close modals on outside click
        window.onclick = function(event) {
            if (event.target.className === 'modal') {
                event.target.style.display = 'none';
            }
        }
    </script>
</body>
</html>"""
    return web.Response(text=html_content, content_type="text/html")
    return web.Response(text=html_content, content_type="text/html")


async def health_check(request):
    """Health check endpoint."""
    _LOGGER.debug("Health check called from %s", request.remote)
    health_status = {
        "status": "ok",
        "service": "squid_proxy_manager",
        "manager_initialized": manager is not None,
        "version": "1.1.15",
    }
    _LOGGER.info(
        "Health check - status: ok, manager: %s", "initialized" if manager else "not initialized"
    )
    return web.json_response(health_status)


async def get_instances(request):
    """Get list of proxy instances."""
    _LOGGER.debug("GET /api/instances called from %s", request.remote)
    if manager is None:
        _LOGGER.warning("GET /api/instances called but manager is not initialized")
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        _LOGGER.info("Retrieving list of proxy instances")
        instances = await manager.get_instances()
        _LOGGER.info("Retrieved %d proxy instances", len(instances))
        return web.json_response({"instances": instances, "count": len(instances)})
    except Exception as ex:
        _LOGGER.error("Failed to get instances: %s", ex, exc_info=True)
        return web.json_response({"error": str(ex)}, status=500)


async def create_instance(request):
    """Create a new proxy instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        data = await request.json()
        name = data.get("name")
        port = data.get("port", 3128)
        https_enabled = data.get("https_enabled", False)
        users = data.get("users", [])

        if not name:
            return web.json_response({"error": "Instance name is required"}, status=400)

        instance = await manager.create_instance(
            name=name,
            port=port,
            https_enabled=https_enabled,
            users=users,
        )

        return web.json_response({"status": "created", "instance": instance}, status=201)
    except Exception as ex:
        _LOGGER.error("Failed to create instance: %s", ex)
        return web.json_response({"error": str(ex)}, status=500)


async def start_instance(request):
    """Start a proxy instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        if not name:
            return web.json_response({"error": "Instance name is required"}, status=400)

        success = await manager.start_instance(name)
        if success:
            return web.json_response({"status": "started", "instance": name})
        else:
            return web.json_response({"error": "Failed to start instance"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to start instance: %s", ex)
        return web.json_response({"error": str(ex)}, status=500)


async def stop_instance(request):
    """Stop a proxy instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        if not name:
            return web.json_response({"error": "Instance name is required"}, status=400)

        # Verify instance exists
        instances = await manager.get_instances()
        if not any(i["name"] == name for i in instances):
            return web.json_response({"error": f"Instance {name} not found"}, status=404)

        success = await manager.stop_instance(name)
        if success:
            return web.json_response({"status": "stopped", "instance": name})
        else:
            return web.json_response({"error": "Failed to stop instance"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to stop instance %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def remove_instance(request):
    """Remove a proxy instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        if not name:
            return web.json_response({"error": "Instance name is required"}, status=400)

        success = await manager.remove_instance(name)
        if success:
            return web.json_response({"status": "removed", "instance": name})
        else:
            return web.json_response({"error": "Failed to remove instance"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to remove instance: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def get_instance_users(request):
    """Get users for an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        users = await manager.get_users(name)
        return web.json_response({"users": users})
    except Exception as ex:
        _LOGGER.error("Failed to get users for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def add_instance_user(request):
    """Add a user to an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return web.json_response({"error": "Username and password are required"}, status=400)

        success = await manager.add_user(name, username, password)
        if success:
            return web.json_response({"status": "user_added"})
        return web.json_response({"error": "Failed to add user"}, status=500)
    except ValueError as ex:
        _LOGGER.warning("Validation error adding user to %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=400)
    except Exception as ex:
        _LOGGER.error("Failed to add user to %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def remove_instance_user(request):
    """Remove a user from an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        username = request.match_info.get("username")

        if not username:
            return web.json_response({"error": "Username is required"}, status=400)

        success = await manager.remove_user(name, username)
        if success:
            return web.json_response({"status": "user_removed"})
        return web.json_response({"error": "Failed to remove user"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to remove user from %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def get_instance_logs(request):
    """Get logs for an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        log_type = request.query.get("type", "cache")  # 'cache' or 'access'

        from proxy_manager import LOGS_DIR

        log_file = LOGS_DIR / name / f"{log_type}.log"

        if not log_file.exists():
            return web.Response(text=f"Log file {log_type}.log not found.")

        # Return last 100 lines
        with open(log_file) as f:
            lines = f.readlines()
            return web.Response(text="".join(lines[-100:]))
    except Exception as ex:
        _LOGGER.error("Failed to get logs for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def update_instance_settings(request):
    """Update instance settings."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        data = await request.json()
        port = data.get("port")
        https_enabled = data.get("https_enabled")

        success = await manager.update_instance(name, port, https_enabled)
        if success:
            return web.json_response({"status": "updated"})
        return web.json_response({"error": "Failed to update settings"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to update settings for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def regenerate_instance_certs(request):
    """Regenerate certificates for an instance."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        success = await manager.regenerate_certs(name)
        if success:
            return web.json_response({"status": "certs_regenerated"})
        return web.json_response({"error": "Failed to regenerate certificates"}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to regenerate certificates for %s: %s", name, ex)
        return web.json_response({"error": str(ex)}, status=500)


async def test_instance_connectivity(request):
    """Test proxy instance connectivity."""
    if manager is None:
        return web.json_response({"error": "Manager not initialized"}, status=503)
    try:
        name = request.match_info.get("name")
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return web.json_response({"error": "Username and password are required"}, status=400)

        # Get instance details
        instances = await manager.get_instances()
        instance = next((i for i in instances if i["name"] == name), None)
        if not instance:
            return web.json_response({"error": "Instance not found"}, status=404)

        if not instance.get("running", False):
            return web.json_response({"error": "Instance is not running"}, status=400)

        # Test connectivity using subprocess curl
        import subprocess
        protocol = "https" if instance.get("https_enabled", False) else "http"
        proxy_url = f"{protocol}://{username}:{password}@localhost:{instance['port']}"

        try:
            result = subprocess.run(
                [
                    "curl",
                    "-x",
                    proxy_url,
                    "-s",
                    "-o",
                    "/dev/null",
                    "-w",
                    "%{http_code}",
                    "http://www.google.com",
                    "--max-time",
                    "10",
                    "--connect-timeout",
                    "5",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            success = result.returncode == 0 and result.stdout.strip() in ["200", "301", "302", "307"]

            return web.json_response(
                {
                    "status": "success" if success else "failed",
                    "http_code": result.stdout.strip() if result.returncode == 0 else None,
                    "error": result.stderr if not success and result.stderr else None,
                    "message": f"Connection {'succeeded' if success else 'failed'}",
                }
            )
        except subprocess.TimeoutExpired:
            return web.json_response({"status": "failed", "error": "Connection timeout"}, status=500)
        except Exception as curl_ex:
            _LOGGER.error("Curl test failed: %s", curl_ex)
            return web.json_response({"status": "failed", "error": str(curl_ex)}, status=500)
    except Exception as ex:
        _LOGGER.error("Failed to test connectivity: %s", ex)
        return web.json_response({"error": str(ex)}, status=500)


async def start_app():
    """Start the web application."""
    _LOGGER.info("Initializing web application...")
    app = web.Application()

    app.middlewares.append(normalize_path_middleware)
    app.middlewares.append(logging_middleware)

    # Root and health routes (for ingress health checks)
    # With ingress_entry: /, all routes are accessible directly
    _LOGGER.info("Registering routes...")
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_check)

    # API routes
    app.router.add_get("/api/instances", get_instances)
    app.router.add_post("/api/instances", create_instance)
    app.router.add_patch("/api/instances/{name}", update_instance_settings)
    app.router.add_post("/api/instances/{name}/start", start_instance)
    app.router.add_post("/api/instances/{name}/stop", stop_instance)
    app.router.add_delete("/api/instances/{name}", remove_instance)
    app.router.add_post("/api/instances/{name}/certs", regenerate_instance_certs)
    app.router.add_get("/api/instances/{name}/logs", get_instance_logs)

    # User management API
    app.router.add_get("/api/instances/{name}/users", get_instance_users)
    app.router.add_post("/api/instances/{name}/users", add_instance_user)
    app.router.add_delete("/api/instances/{name}/users/{username}", remove_instance_user)
    app.router.add_post("/api/instances/{name}/test", test_instance_connectivity)

    _LOGGER.info("Routes registered: / (web UI), /health, /api/instances")

    _LOGGER.info("Setting up AppRunner...")
    runner = web.AppRunner(app)
    await runner.setup()
    _LOGGER.info("AppRunner setup complete")

    # Use fixed ingress port (8099) as configured in config.yaml
    _LOGGER.info("Determining ingress port...")
    port = get_ingress_port()
    _LOGGER.info("Starting TCP site on 0.0.0.0:%d...", port)

    try:
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        _LOGGER.info("✓ TCP site started successfully on port %d", port)

        # Give the server a moment to fully bind
        await asyncio.sleep(0.5)

        # Verify server is responding to HTTP requests (what ingress will actually do)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://127.0.0.1:{port}/health", timeout=aiohttp.ClientTimeout(total=2)
                ) as response:
                    if response.status == 200:
                        _LOGGER.info("✓ Verified HTTP server is responding on port %d", port)
                    else:
                        _LOGGER.warning(
                            "⚠ HTTP server responded with status %d on port %d",
                            response.status,
                            port,
                        )
        except Exception as ex:
            _LOGGER.warning("⚠ Could not verify HTTP server is responding on port %d: %s", port, ex)
    except OSError as ex:
        _LOGGER.error("✗ Failed to start TCP site on port %d: %s", port, ex, exc_info=True)
        raise
    except Exception as ex:
        _LOGGER.error("✗ Unexpected error starting TCP site: %s", ex, exc_info=True)
        raise

    _LOGGER.info("=" * 60)
    _LOGGER.info("✓ Squid Proxy Manager API started successfully")
    _LOGGER.info("  Listening on: 0.0.0.0:%d", port)
    _LOGGER.info(
        "  Ingress URL: http://supervisor/ingress/%s",
        os.getenv("SUPERVISOR_TOKEN", "unknown")[:8]
        if os.getenv("SUPERVISOR_TOKEN")
        else "unknown",
    )
    _LOGGER.info("  Server is ready to accept connections from ingress")
    _LOGGER.info("=" * 60)
    return runner


async def main():
    """Main function."""
    global manager

    _LOGGER.info("=" * 60)
    _LOGGER.info("Starting Squid Proxy Manager add-on v1.1.15")
    _LOGGER.info("=" * 60)
    _LOGGER.info("Python version: %s", sys.version)
    _LOGGER.info("Log level: %s", LOG_LEVEL)
    _LOGGER.info("Config path: %s (exists: %s)", CONFIG_PATH, CONFIG_PATH.exists())
    _LOGGER.info("HA API URL: %s", HA_API_URL)

    runner = None
    try:
        # Start web API FIRST so ingress can connect even if manager init fails
        _LOGGER.info("Step 1/3: Starting web server...")
        runner = await start_app()
        _LOGGER.info("✓ Web server started successfully")
        _LOGGER.info("Server is now accessible via ingress")

        # Initialize manager with error handling
        _LOGGER.info("Step 2/3: Initializing ProxyInstanceManager...")
        try:
            manager = ProxyInstanceManager()
            _LOGGER.info("✓ Manager initialized successfully")
        except Exception as ex:
            _LOGGER.error("✗ Failed to initialize manager: %s", ex, exc_info=True)
            manager = None

        # Load configuration and create instances from config (only if manager is available)
        _LOGGER.info("Step 3/3: Loading configuration and creating instances...")
        if manager is not None:
            try:
                _LOGGER.info("Loading configuration from %s", CONFIG_PATH)
                config = await get_config()
                instances_config = config.get("instances", [])
                _LOGGER.info("Loaded configuration: %d instance(s) defined", len(instances_config))

                # Create instances from configuration
                for idx, instance_config in enumerate(instances_config, 1):
                    try:
                        name = instance_config.get("name")
                        port = instance_config.get("port", 3128)
                        https_enabled = instance_config.get("https_enabled", False)
                        users = instance_config.get("users", [])

                        _LOGGER.info(
                            "[%d/%d] Creating instance: name=%s, port=%d, https=%s, users=%d",
                            idx,
                            len(instances_config),
                            name,
                            port,
                            https_enabled,
                            len(users),
                        )
                        await manager.create_instance(
                            name=name,
                            port=port,
                            https_enabled=https_enabled,
                            users=users,
                        )
                        _LOGGER.info("✓ Instance '%s' created successfully", name)
                    except Exception as ex:
                        _LOGGER.error(
                            "✗ Failed to create instance '%s': %s",
                            instance_config.get("name"),
                            ex,
                            exc_info=True,
                        )
                _LOGGER.info("Configuration processing complete")
            except Exception as ex:
                _LOGGER.error("✗ Failed to load configuration: %s", ex, exc_info=True)
        else:
            _LOGGER.warning("Skipping instance creation - manager not initialized")

        _LOGGER.info("=" * 60)
        _LOGGER.info("✓ Squid Proxy Manager add-on started successfully")
        _LOGGER.info("Server status: RUNNING")
        _LOGGER.info("Manager status: %s", "INITIALIZED" if manager else "NOT INITIALIZED")
        _LOGGER.info("Ready to accept requests")
        _LOGGER.info("=" * 60)

        # Keep running
        _LOGGER.info("Entering main event loop...")
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            _LOGGER.info("Received keyboard interrupt, shutting down...")
        except Exception as ex:
            _LOGGER.error("Unexpected error in main event loop: %s", ex, exc_info=True)
            raise
    except Exception as ex:
        _LOGGER.critical("Fatal error during startup: %s", ex, exc_info=True)
        _LOGGER.critical("Add-on failed to start properly")
        raise
    finally:
        _LOGGER.info("Cleaning up...")
        if runner:
            try:
                await runner.cleanup()
                _LOGGER.info("Server cleanup complete")
            except Exception as ex:
                _LOGGER.error("Error during cleanup: %s", ex, exc_info=True)
        _LOGGER.info("Shutdown complete")


if __name__ == "__main__":
    try:
        _LOGGER.info("Entering main execution block")
        _LOGGER.info("Starting asyncio event loop...")
        asyncio.run(main())
    except KeyboardInterrupt:
        if "_LOGGER" in globals():
            _LOGGER.info("Interrupted by user")
        else:
            print("Interrupted by user", file=sys.stderr)
        sys.exit(0)
    except Exception as ex:
        if "_LOGGER" in globals():
            _LOGGER.critical("Fatal error in main execution: %s", ex, exc_info=True)
        else:
            print(f"CRITICAL: Fatal error in main execution: {ex}", file=sys.stderr)
            import traceback

            traceback.print_exc()
        sys.exit(1)
