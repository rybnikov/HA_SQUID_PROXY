# E2E Test Fixes for UI Redesign v1.5.2+

## Summary
Fixed 9 failing E2E tests to adapt to the new UI design where:
1. Logs moved from settings page to modal dialog
2. Instance cards use visual status indicators (no "Running"/"Stopped" text)
3. Stopped instances show GRAY color scheme (not red)

## Files Modified

### 1. `/tests/e2e/utils.py`
**Changes:**
- Updated `is_error_color()` function to detect gray/secondary colors for stopped state
- Added detection for empty string (indicates no status dot = stopped)
- Updated docstring to reflect new UI design expectations

**Before:** Checked for red color (`#db4437`, `rgb(219, 68, 55)`)
**After:** Checks for gray/secondary colors (`#9b9b9b`, `rgba(158, 158, 158, ...)`, empty string)

### 2. `/tests/e2e/test_edge_cases.py`
**Fixed 3 tests:**

#### `test_empty_logs_display` (line 185-212)
- **Issue:** Looked for logs section directly on settings page
- **Fix:** Added click on `[data-testid="settings-view-logs-button"]` to open dialog first
- **Pattern:** Navigate → Click VIEW LOGS → Wait for dialog → Assert logs section exists

#### `test_instance_card_displays_all_info` (line 217-238)
- **Issue:** Checked for "Running" text in card
- **Fix:** Check for visual indicator - presence of stop button when running
- **Pattern:** Verify name + port in text, then check `instance-stop-chip` button exists

#### `test_settings_page_has_all_sections` (line 243-276)
- **Issue:** Looked for "Instance Logs" h2 section
- **Fix:** Check for VIEW LOGS button instead
- **Pattern:** Verify all h2 sections exist, plus `settings-view-logs-button` for logs section

### 3. `/tests/e2e/test_scenarios.py`
**Fixed 6 tests:**

#### `test_scenario_4_monitor_logs` (line 192-230)
- **Issue:** Expected logs section directly on settings page
- **Fix:** Added click on `settings-view-logs-button` to open dialog
- **Pattern:** Same as `test_empty_logs_display`

#### Icon Color Tests (5 tests)
All updated with:
- Changed assertion messages from "red" to "gray/stopped"
- Updated docstrings to reflect new design (gray for stopped, not red)
- Tests still validate the original bug fix (running = green regardless of HTTP/HTTPS)

**Tests updated:**
1. `test_server_icon_color_reflects_status` (line 545-601)
2. `test_icon_color_multiple_instances_mixed_status` (line 606-665)
3. `test_icon_color_https_not_red_when_running` (line 670-709)
4. `test_icon_color_rapid_status_changes` (line 714-761)
5. `test_icon_color_persistence_after_page_refresh` (line 798-848)

## Test Patterns Documented

### Opening Logs Dialog
```python
await navigate_to_settings(page, instance_name)
await page.click('[data-testid="settings-view-logs-button"]')
await page.wait_for_selector('[data-testid="logs-type-select"]', timeout=5000)
```

### Checking Card Status (Visual)
```python
# Running instance shows stop button
stop_button = await page.query_selector(f'[data-testid="instance-stop-chip-{name}"]')
assert stop_button is not None

# OR check icon color
icon_color = await get_icon_color(page, instance_name)
assert is_success_color(icon_color)  # Green = running
assert is_error_color(icon_color)     # Gray = stopped
```

## Color Expectations

| State   | Background Tint        | Icon Color | Status Dot |
|---------|------------------------|------------|------------|
| Running | `rgba(67,160,71,0.15)` | Green      | Green      |
| Stopped | `rgba(158,158,158,0.15)` | Gray     | None       |

## Validation
All modified files pass Python syntax check:
- ✓ `tests/e2e/test_edge_cases.py`
- ✓ `tests/e2e/test_scenarios.py`
- ✓ `tests/e2e/utils.py`

## Next Steps
Run the test suite to verify all fixes:
```bash
./run_tests.sh e2e
```

Expected result: All 9 previously failing tests should now pass.
