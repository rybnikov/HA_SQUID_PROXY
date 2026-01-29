# Comprehensive Test Plan: HA Squid Proxy Manager

This plan covers end-to-end (E2E) testing of the Squid Proxy Manager add-on, from installation to multi-instance operation.

## 1. Installation & Initialization

- **Case 1.1: Clean Startup**
  - Scenario: Add-on starts with no existing configuration.
  - Expected: `ProxyInstanceManager` initializes, log directories are created, and Web UI is accessible via Ingress.
- **Case 1.2: Startup with Options**
  - Scenario: Add-on starts with instances defined in `options.json`.
  - Expected: Instances are automatically created and started on launch.

## 2. Web UI Management (UI E2E)

- **Case 2.1: Add Instance Modal**
  - Action: Click "+ Add Instance", fill name "proxy1", port 3128, enable HTTPS.
  - Expected: Instance appears in the list with "starting" or "running" status.
- **Case 2.2: User Management**
  - Action: Open "Users" modal for "proxy1", add "user1" with "pass123456".
  - Expected: "user1" appears in the user list.
- **Case 2.3: Duplicate User Handling**
  - Action: Try to add "user1" again to the same instance.
  - Expected: Error message "User testuser already exists" is displayed (Status 400).
- **Case 2.4: Log Viewing & Switching**
  - Action: Open "Logs" modal, switch between "Cache Log" and "Access Log".
  - Expected: Log content updates correctly and displays the relevant log for the selected instance.
- **Case 2.5: Settings Update**
  - Action: Open "Settings" modal, change port to 3129, disable HTTPS.
  - Expected: Instance restarts and status updates to "running" on the new port.

## 3. Proxy Functionality (Functional E2E)

- **Case 3.1: Multi-Instance Isolation**
  - Setup: Create "proxy-alpha" (3130) and "proxy-beta" (3131).
  - Action: Connect to 3130 with alpha credentials, and 3131 with beta credentials.
  - Expected: Traffic flows through both correctly. Cross-connection (alpha credentials on beta port) should fail.
- **Case 3.2: HTTP Traffic**
  - Action: `curl -x http://user:pass@IP:3130 http://google.com`.
  - Expected: 200 OK.
- **Case 3.3: HTTPS Tunneling (via CONNECT)**
  - Action: `curl -x http://user:pass@IP:3130 https://google.com`.
  - Expected: 200 OK (Connection established).
- **Case 3.4: HTTPS Proxy (Native SSL)**
  - Setup: Instance with `https_enabled: true`.
  - Action: `curl -x https://user:pass@IP:3130 --proxy-insecure https://google.com`.
  - Expected: 200 OK.

## 4. Resilience & Persistence

- **Case 4.1: Manager Restart**
  - Action: Stop and start the management process (main.py).
  - Expected: Child Squid processes are tracked and reported as running after manager recovery.
- **Case 4.2: Data Persistence**
  - Action: Delete the add-on container and recreate it (simulating HA update).
  - Expected: All instance configs, users, and certificates in `/data` are preserved and reloaded.

## 5. Security & Validation

- **Case 5.1: Path Normalization**
  - Action: Access API via `//api//instances`.
  - Expected: 200 OK (Middleware handles extra slashes).
- **Case 5.2: Invalid Input Validation**
  - Action: Create instance with invalid characters in name or port already in use.
  - Expected: Meaningful error message returned by the API.

## 6. Bug Fixes & New Features

- **Case 6.1: Multiple Users Per Instance**
  - Action: Add multiple users (user1, user2, user3) to the same instance via UI.
  - Expected: All users are added successfully and can authenticate independently.
- **Case 6.2: User Isolation Between Instances**
  - Setup: Create two instances with the same username but different passwords.
  - Action: Test authentication on each instance.
  - Expected: Users are isolated - credentials from instance1 don't work on instance2.
- **Case 6.3: Remove Instance**
  - Action: Create instance, then delete it via UI Delete button.
  - Expected: Instance is removed from UI and API, all directories cleaned up.
- **Case 6.4: Stop Button Functionality**
  - Action: Create instance, click Stop button.
  - Expected: Instance status changes to "stopped" and API confirms it's not running.
- **Case 6.5: Test Button Functionality**
  - Action: Create instance with user, click Test button, enter credentials, run test.
  - Expected: Test modal appears, connectivity test runs, results show success/failure with HTTP code.
