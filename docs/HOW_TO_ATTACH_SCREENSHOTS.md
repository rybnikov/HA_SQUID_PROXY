# How to Attach Screenshots to Pull Requests

This guide explains how to capture and attach screenshots to PRs without committing them to the repository.

## Why Screenshots Aren't Committed

- **Repository Size**: Binary image files bloat the repository
- **Git History**: Images create large, unwieldy commits
- **Temporary Nature**: Screenshots are for PR review, not permanent docs
- **GitHub Hosting**: GitHub provides free hosting for PR attachments
- **Easy Updates**: Simply add a new comment with updated screenshots

## Quick Workflow

### 1. Generate Screenshots

For frontend mock mode:
```bash
# Start the frontend in mock mode
./run_frontend_for_agent.sh

# Use Playwright MCP or open browser at http://localhost:5173
# Capture screenshots with Playwright or your screenshot tool

# Stop the server
./run_frontend_for_agent.sh --stop
```

Screenshots from Playwright MCP are saved to `/tmp/playwright-logs/` by default.

### 2. Locate Your Screenshots

```bash
# Check Playwright screenshots
ls /tmp/playwright-logs/*.png

# Or if using a browser screenshot tool
# Screenshots are typically in ~/Downloads/ or ~/Pictures/
```

### 3. Attach to GitHub PR

**Method 1: Drag and Drop (Recommended)**
1. Open your PR on GitHub
2. Click "Edit" on the PR description or write a comment
3. Drag and drop your screenshot files into the text box
4. GitHub will upload and insert markdown like: `![image](https://github.com/user-attachments/assets/...)`
5. Add context/description around the images
6. Click "Update comment" or "Comment"

**Method 2: Clipboard Paste**
1. Open your screenshot in an image viewer
2. Copy the image to clipboard (Ctrl+C / Cmd+C)
3. Open your PR on GitHub
4. Click in the comment box
5. Paste (Ctrl+V / Cmd+V)
6. GitHub will upload the image automatically

**Method 3: Issue Attachments**
1. Open your PR on GitHub
2. Scroll to the comment box at the bottom
3. Click the "Attach files by dragging & dropping, selecting or pasting them" link
4. Select your screenshot files
5. Wait for upload to complete
6. Add description and submit comment

## Best Practices

### Naming Screenshots
Use descriptive names:
- ✅ `dashboard-with-3-instances.png`
- ✅ `proxy-settings-modal-https-enabled.png`
- ✅ `error-state-invalid-port.png`
- ❌ `screenshot1.png`
- ❌ `image.png`

### Organizing Multiple Screenshots
When adding multiple screenshots to a PR:

1. **Add context**: Explain what each screenshot shows
2. **Use headings**: Organize with markdown headers
3. **Before/After**: Show comparisons when relevant

Example:
```markdown
## Screenshots

### Dashboard View
![Dashboard](url-to-dashboard.png)
The dashboard now shows 3 mock instances with status indicators.

### Settings Modal
![Settings](url-to-settings.png)
The settings modal includes HTTPS toggle and port configuration.

### Before/After Comparison
**Before:**
![Before](url-to-before.png)

**After:**
![After](url-to-after.png)
The button styling has been updated to match the design system.
```

### Screenshot Quality
- **Resolution**: Use high enough resolution to be readable (1920x1080 or higher)
- **Format**: PNG is preferred for UI screenshots (better quality than JPG)
- **Size**: Keep individual files under 5 MB when possible
- **Crop**: Crop to relevant area to focus attention

## Example: Complete Workflow

```bash
# 1. Make your code changes
git checkout -b feature/new-ui-component

# 2. Test your changes locally
./run_frontend_for_agent.sh

# 3. Capture screenshots with Playwright
playwright-browser_navigate http://localhost:5173
playwright-browser_wait_for 2
playwright-browser_take_screenshot feature-dashboard.png
playwright-browser_click '[data-testid="settings-button"]'
playwright-browser_take_screenshot feature-settings-modal.png

# 4. Stop server
./run_frontend_for_agent.sh --stop

# 5. Commit your code changes (not screenshots!)
git add src/
git commit -m "Add new UI component"
git push origin feature/new-ui-component

# 6. Create PR on GitHub

# 7. Copy screenshots to accessible location
cp /tmp/playwright-logs/feature-*.png ~/pr-screenshots/

# 8. Open PR on GitHub and drag-drop screenshots into the description

# 9. Add context and submit PR
```

## Updating Screenshots

If you need to update screenshots after review feedback:

1. Make the requested changes
2. Generate new screenshots with the same workflow
3. Add a new comment to the PR with updated screenshots
4. Reference the specific feedback: "Updated per @reviewer's feedback: ..."

No need to delete old screenshots - they provide a history of iterations.

## Troubleshooting

### Screenshots Not Uploading
- **File too large**: Compress or resize (GitHub limit is 10 MB)
- **Wrong format**: Convert to PNG or JPG
- **Browser issue**: Try a different browser or use drag-and-drop

### Lost Screenshots
If you lost your local screenshots but they're in the PR:
- Right-click on the image in GitHub
- Select "Save image as..."
- Download to regenerate locally if needed

### Screenshot Location Unknown
```bash
# Find recent PNG files
find ~ -name "*.png" -type f -mtime -1

# Check common locations
ls ~/Downloads/
ls ~/Pictures/
ls /tmp/playwright-logs/
```

## Summary

✅ **DO**: Generate screenshots locally and attach via GitHub
❌ **DON'T**: Commit screenshot files to the repository
✅ **DO**: Use descriptive names and add context
❌ **DON'T**: Let screenshots accumulate in your local directories
✅ **DO**: Update screenshots when making changes
❌ **DON'T**: Forget to regenerate after significant UI changes

Following these practices keeps the repository clean while providing reviewers with the visual context they need.
