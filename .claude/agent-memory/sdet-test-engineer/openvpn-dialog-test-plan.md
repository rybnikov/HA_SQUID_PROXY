# OpenVPN Patcher Dialog - Test Implementation Plan

**Task #4: Write tests for dialog implementation**
**Status: READY - Waiting for Task #3 completion**
**Estimated Time: 90 minutes**

## Test File Changes

### 1. Frontend Component Tests

**File**: `squid_proxy_manager/frontend/src/features/instances/tabs/OpenVPNPatcherDialog.test.tsx` (new)
**Source**: Migrate from `OpenVPNTab.test.tsx`

**Test Count**: ~25 tests
- 13 migrated tests (existing functionality)
- 12 new tests (dialog behavior, inline errors, accessibility)

### 2. E2E Browser Tests

**File**: `tests/e2e/test_ovpn_patcher_e2e.py` (update)

**Test Count**: ~5 scenarios
- 3 updated scenarios (dialog workflow)
- 2 new scenarios (dialog triggers)

## Test Priority Matrix

### P0 - Production Blockers (MUST PASS)

**Critical: No window.alert() calls**

```typescript
test('file validation shows inline error, no alert', async () => {
  const alertSpy = vi.spyOn(window, 'alert');
  const fileInput = screen.getByTestId('openvpn-file-input');
  const invalidFile = new File(['data'], 'test.txt', { type: 'text/plain' });

  Object.defineProperty(fileInput, 'files', {
    value: [invalidFile],
    writable: false,
  });
  fireEvent.change(fileInput);

  // Inline error shown
  expect(screen.getByText(/valid .ovpn file/i)).toBeTruthy();

  // NO alert() called
  expect(alertSpy).not.toHaveBeenCalled();
  alertSpy.mockRestore();
});

test('API patch error shows inline message, no alert', async () => {
  const alertSpy = vi.spyOn(window, 'alert');
  vi.mocked(instancesApi.patchOVPNConfig).mockRejectedValue(
    new Error('Invalid config format')
  );

  // Upload file and click patch
  await uploadFile('test.ovpn');
  await clickPatchButton();

  await waitFor(() => {
    expect(screen.getByText(/Invalid config format/i)).toBeTruthy();
  });

  expect(alertSpy).not.toHaveBeenCalled();
  alertSpy.mockRestore();
});

test('copy success shows inline message, no alert', async () => {
  const alertSpy = vi.spyOn(window, 'alert');

  // Mock clipboard
  const writeTextMock = vi.fn().mockResolvedValue(undefined);
  Object.assign(navigator, {
    clipboard: { writeText: writeTextMock },
  });

  // Patch config then copy
  await patchConfig();
  const copyButton = screen.getByTestId('openvpn-copy');
  fireEvent.click(copyButton);

  await waitFor(() => {
    expect(screen.getByText(/Copied to clipboard/i)).toBeTruthy();
  });

  expect(alertSpy).not.toHaveBeenCalled();
  alertSpy.mockRestore();
});
```

### P1 - Component Behavior Changes

**HASwitch (not checkbox)**

```typescript
test('auth toggle is HASwitch component', () => {
  renderDialog({ proxyType: 'squid' });

  const authToggle = screen.getByTestId('openvpn-auth-toggle');
  expect(authToggle.tagName.toLowerCase()).toBe('ha-switch');
});

test('HASwitch toggle shows/hides auth fields', async () => {
  renderDialog({ proxyType: 'squid' });

  const authToggle = screen.getByTestId('openvpn-auth-toggle');

  // Initially hidden
  expect(screen.queryByTestId('openvpn-username-input')).toBeNull();

  // Click toggle
  fireEvent.click(authToggle);

  // Fields visible
  await waitFor(() => {
    expect(screen.getByTestId('openvpn-username-input')).toBeTruthy();
    expect(screen.getByTestId('openvpn-password-input')).toBeTruthy();
  });
});
```

**File Upload Button**

```typescript
test('file selection via HAButton triggers hidden input', () => {
  renderDialog({ proxyType: 'squid' });

  const selectButton = screen.getByTestId('openvpn-file-select-button');
  const fileInput = screen.getByTestId('openvpn-file-input');

  // Button shows "Select .ovpn File"
  expect(selectButton.textContent).toContain('Select .ovpn File');

  // Input is hidden
  expect(fileInput).toHaveStyle({ display: 'none' });
});

test('button text changes after file upload', async () => {
  renderDialog({ proxyType: 'squid' });

  const selectButton = screen.getByTestId('openvpn-file-select-button');
  const fileInput = screen.getByTestId('openvpn-file-input');

  // Upload file
  const file = new File(['content'], 'test.ovpn', { type: 'text/plain' });
  Object.defineProperty(fileInput, 'files', {
    value: [file],
    writable: false,
  });
  fireEvent.change(fileInput);

  // Button text changes
  await waitFor(() => {
    expect(selectButton.textContent).toContain('Change File');
  });

  // Filename display
  expect(screen.getByText(/test.ovpn/)).toBeTruthy();
});
```

### P2 - Dialog Lifecycle

```typescript
describe('Dialog Lifecycle', () => {
  test('dialog opens when isOpen=true', () => {
    renderDialog({ isOpen: true });
    expect(screen.getByTestId('openvpn-dialog')).toBeTruthy();
  });

  test('dialog hidden when isOpen=false', () => {
    renderDialog({ isOpen: false });
    expect(screen.queryByTestId('openvpn-dialog')).toBeNull();
  });

  test('closes on Close button click', () => {
    const onClose = vi.fn();
    renderDialog({ isOpen: true, onClose });

    const closeButton = screen.getByTestId('openvpn-dialog-close');
    fireEvent.click(closeButton);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('closes on Escape key', () => {
    const onClose = vi.fn();
    renderDialog({ isOpen: true, onClose });

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('dialog has focus trap', async () => {
    renderDialog({ isOpen: true, proxyType: 'squid' });

    const dialog = screen.getByTestId('openvpn-dialog');

    // Tab through all focusable elements
    fireEvent.keyDown(document.activeElement!, { key: 'Tab' });
    await waitFor(() => {
      expect(dialog).toContainElement(document.activeElement);
    });

    // Multiple tabs should stay inside dialog
    for (let i = 0; i < 5; i++) {
      fireEvent.keyDown(document.activeElement!, { key: 'Tab' });
      await waitFor(() => {
        expect(dialog).toContainElement(document.activeElement);
      });
    }
  });
});
```

### P3 - Edge Cases

```typescript
test('shows external IP warning when missing', () => {
  renderDialog({ externalIp: undefined });

  expect(screen.getByText(/External IP not/i)).toBeTruthy();
  expect(screen.getByText(/General settings/i)).toBeTruthy();
});

test('hides external IP warning when provided', () => {
  renderDialog({ externalIp: '1.2.3.4' });

  expect(screen.queryByText(/External IP not/i)).toBeNull();
});

test('shows auth section for Squid only', () => {
  const { rerender } = renderDialog({ proxyType: 'squid' });
  expect(screen.getByTestId('openvpn-auth-toggle')).toBeTruthy();

  rerender(<OpenVPNPatcherDialog proxyType="tls_tunnel" />);
  expect(screen.queryByTestId('openvpn-auth-toggle')).toBeNull();
});

test('copy success message auto-hides after 3s', async () => {
  vi.useFakeTimers();

  await patchConfig();
  const copyButton = screen.getByTestId('openvpn-copy');
  fireEvent.click(copyButton);

  // Message appears
  expect(screen.getByText(/Copied to clipboard/i)).toBeTruthy();

  // Fast-forward 3s
  vi.advanceTimersByTime(3000);

  // Message disappears
  await waitFor(() => {
    expect(screen.queryByText(/Copied to clipboard/i)).toBeNull();
  });

  vi.useRealTimers();
});
```

### P4 - Accessibility

```typescript
test('dialog has proper ARIA attributes', () => {
  renderDialog({ isOpen: true });

  const dialog = screen.getByTestId('openvpn-dialog');

  expect(dialog).toHaveAttribute('role', 'dialog');
  expect(dialog).toHaveAttribute('aria-labelledby');
});

test('all interactive elements have accessible names', () => {
  renderDialog({ isOpen: true, proxyType: 'squid' });

  const selectButton = screen.getByTestId('openvpn-file-select-button');
  const patchButton = screen.getByTestId('openvpn-patch-button');
  const closeButton = screen.getByTestId('openvpn-dialog-close');

  expect(selectButton).toHaveAccessibleName();
  expect(patchButton).toHaveAccessibleName();
  expect(closeButton).toHaveAccessibleName();
});
```

## E2E Test Updates

### File: `tests/e2e/test_ovpn_patcher_e2e.py`

**Changes Required:**

1. **Update navigation pattern** (OLD vs NEW):

```python
# OLD: Navigate to tab
await page.click('[data-testid="tab-openvpn"]')

# NEW: Open dialog from settings
await page.click('[data-testid="open-openvpn-patcher-button"]')
await page.wait_for_selector('[data-testid="openvpn-dialog"]', timeout=5000)
```

2. **Add dialog trigger tests**:

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_open_dialog_from_connection_info(browser, unique_name, unique_port):
    """E2E: Open OpenVPN patcher dialog from Connection Info section (TLS tunnel)."""
    instance_name = unique_name("tls-dialog")
    port = unique_port(4600)

    page = await browser.new_page()
    try:
        # Create TLS tunnel instance
        await create_tls_tunnel_instance(page, instance_name, port)
        await navigate_to_settings(page, instance_name)

        # Connection Info section should have "Patch OpenVPN Config" button
        await page.wait_for_selector('[data-testid="connection-info-open-openvpn-button"]')
        await page.click('[data-testid="connection-info-open-openvpn-button"]')

        # Dialog opens
        await page.wait_for_selector('[data-testid="openvpn-dialog"]', timeout=5000)

        # Verify dialog content for TLS tunnel
        dialog_text = await page.text_content('[data-testid="openvpn-dialog"]')
        assert 'extract your VPN server' in dialog_text.lower()

    finally:
        await page.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_open_dialog_from_test_connectivity(browser, unique_name, unique_port):
    """E2E: Open OpenVPN patcher dialog from Test Connectivity section (Squid)."""
    instance_name = unique_name("squid-dialog")
    port = unique_port(3600)

    page = await browser.new_page()
    try:
        # Create Squid instance
        await create_instance_via_ui(page, ADDON_URL, instance_name, port, https_enabled=False)
        await navigate_to_settings(page, instance_name)

        # Test Connectivity section should have "Patch OpenVPN Config" button
        await page.wait_for_selector('[data-testid="test-connectivity-open-openvpn-button"]')
        await page.click('[data-testid="test-connectivity-open-openvpn-button"]')

        # Dialog opens
        await page.wait_for_selector('[data-testid="openvpn-dialog"]', timeout=5000)

        # Verify dialog content for Squid
        dialog_text = await page.text_content('[data-testid="openvpn-dialog"]')
        assert 'http proxy' in dialog_text.lower()

    finally:
        await page.close()
```

3. **Update existing 3 scenarios**:

```python
async def test_upload_and_patch_ovpn_squid(browser, unique_name, unique_port, api_session):
    """E2E test: Upload and patch .ovpn file via dialog for Squid instance."""
    # ... create instance ...

    # Open dialog (NEW)
    await page.click('[data-testid="open-openvpn-patcher-button"]')
    await page.wait_for_selector('[data-testid="openvpn-dialog"]', timeout=5000)

    # Upload file (selector unchanged)
    file_input = await page.query_selector('[data-testid="openvpn-file-input"]')
    await file_input.set_input_files(str(ovpn_file_path))

    # ... rest of test ...

    # Close dialog when done (NEW)
    await page.click('[data-testid="openvpn-dialog-close"]')
```

## Test Execution Checklist

**Phase 1: Component Tests (45 min)**
- [ ] Create `OpenVPNPatcherDialog.test.tsx`
- [ ] Copy test setup from `OpenVPNTab.test.tsx`
- [ ] Migrate 13 existing tests
- [ ] Add 4 P0 tests (no alert)
- [ ] Add 3 P1 tests (component changes)
- [ ] Add 5 P2 tests (dialog lifecycle)
- [ ] Add 3 P3 tests (edge cases)
- [ ] Add 2 P4 tests (accessibility)
- [ ] Run: `npm run test -- --run`
- [ ] Verify all 25 tests pass

**Phase 2: E2E Tests (30 min)**
- [ ] Update `test_ovpn_patcher_e2e.py`
- [ ] Update 3 existing scenarios
- [ ] Add 2 new trigger tests
- [ ] Run: `./run_tests.sh e2e`
- [ ] Verify all 5 scenarios pass

**Phase 3: Full Suite (15 min)**
- [ ] Run: `./run_tests.sh`
- [ ] Run: `npm run test`
- [ ] Fix any failures
- [ ] Verify coverage
- [ ] Update test plan documentation
- [ ] Mark Task #4 complete

## Open Questions

1. **Success message auto-hide**: Only copy success, or all success messages?
2. **Dialog trigger testids**: Specific per location or shared?
3. **Close button testid**: `openvpn-cancel` or `openvpn-dialog-close`?
4. **Backdrop click**: Should it close dialog or not?

## data-testid Reference

**Dialog Component:**
- `openvpn-dialog` - Dialog container
- `openvpn-dialog-close` - Close button
- `openvpn-file-select-button` - File upload button (HAButton)
- `openvpn-file-input` - Hidden file input
- `openvpn-auth-toggle` - Auth toggle (HASwitch)
- `openvpn-user-select` - User dropdown (HASelect)
- `openvpn-username-input` - Username field (HATextField)
- `openvpn-password-input` - Password field (HATextField)
- `openvpn-patch-button` - Patch button (HAButton)
- `openvpn-preview` - Preview textarea
- `openvpn-download` - Download button (HAButton)
- `openvpn-copy` - Copy button (HAButton)

**Dialog Triggers (TBD):**
- Connection Info section (TLS tunnel)
- Test Connectivity section (Squid)

## Success Criteria

- ✅ All 25 component tests passing
- ✅ All 5 E2E scenarios passing
- ✅ NO `window.alert()` calls anywhere
- ✅ All HA-native components tested
- ✅ Dialog lifecycle fully covered
- ✅ Accessibility verified
- ✅ Backend tests still passing (no changes needed)
