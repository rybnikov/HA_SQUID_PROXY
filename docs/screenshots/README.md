# UI Screenshots Documentation

This directory contains visual documentation for UI changes in the HA Squid Proxy Manager.

## Purpose

For **all UI-related changes** (buttons, modals, forms, layouts, styling), screenshots and visual documentation must be captured and stored here.

## Directory Structure

```
docs/screenshots/
├── README.md                           # This file
├── [feature]-[description]-v[version].md   # Visual documentation
├── [feature]-before-v[version].png     # Before screenshot
├── [feature]-after-v[version].png      # After screenshot
└── ...
```

## When to Add Screenshots

Screenshots are **MANDATORY** for:

1. ✅ **Button changes** - Redesigns, new states, variant changes
2. ✅ **Modal changes** - New modals, layout updates, styling
3. ✅ **Form changes** - New fields, validation UI, layout
4. ✅ **Layout changes** - Dashboard updates, card layouts, responsive design
5. ✅ **Styling changes** - Colors, typography, spacing, borders
6. ✅ **Component changes** - New UI components, variants
7. ✅ **Interaction states** - Hover, active, disabled states

## How to Capture Screenshots

### Option 1: Pre-Release Script (Recommended)

```bash
# Start addon
./run_addon_local.sh start

# Record workflows (generates GIFs and screenshots)
cd pre_release_scripts
./record_workflows.sh

# GIFs saved to docs/gifs/
```

### Option 2: Manual Browser Screenshots

```bash
# 1. Start addon
./run_addon_local.sh start

# 2. Navigate to http://localhost:8099

# 3. Take screenshots:
# - macOS: Cmd+Shift+4
# - Linux: Screenshot tool
# - Windows: Win+Shift+S

# 4. Save to docs/screenshots/
```

### Option 3: E2E Tests

```bash
# Run with screenshot capture
pytest tests/e2e/test_dashboard.py -v --screenshot=on

# Move to docs/screenshots/
```

## Documentation Template

For each UI change, create a markdown file using this template:

```markdown
# [Feature Name] - Visual Documentation (v[version])

## Overview
[Brief description]

## Implementation Details
- **PR**: #[number]
- **Version**: [version]
- **Date**: [YYYY-MM-DD]
- **Changed Files**: [list]

## Before & After

### Before
![Before](path-or-url)
- Description

### After
![After](path-or-url)
- Description

## Code Changes
[Brief code diff or summary]

## Testing Results
- [ ] Linting passed
- [ ] Tests passed
- [ ] Visual verification complete

## Acceptance Criteria
- [ ] Meets design requirements
- [ ] Accessible
- [ ] Responsive
```

## Naming Conventions

### Markdown Files
Format: `[feature]-[description]-v[version].md`

Examples:
- `button-redesign-v1.4.7.md`
- `modal-layout-update-v1.5.0.md`
- `form-validation-ui-v1.6.2.md`

### Screenshot Files
Format: `[feature]-[state]-v[version].png`

Examples:
- `button-redesign-before-v1.4.7.png`
- `button-redesign-after-v1.4.7.png`
- `modal-hover-state-v1.5.0.png`

## Screenshot Quality Standards

Screenshots must:
- ✅ Show the relevant UI component clearly
- ✅ Include context (surrounding UI elements)
- ✅ Be high resolution (at least 1920x1080)
- ✅ Show interaction states when applicable
- ✅ Use consistent browser/viewport size
- ✅ Include both "before" and "after" for changes

## PR Integration

### 1. Commit Screenshots

```bash
git add docs/screenshots/
git commit -m "docs: add screenshots for [feature] UI changes"
```

### 2. Reference in PR Description

```markdown
## Visual Changes

See: [docs/screenshots/feature-name-v1.4.7.md](docs/screenshots/feature-name-v1.4.7.md)

### Before
![Before](docs/screenshots/feature-before.png)

### After
![After](docs/screenshots/feature-after.png)
```

### 3. PR Review Checklist

Before marking ready for review:
- [ ] Screenshots captured and committed
- [ ] Visual documentation created
- [ ] PR description includes screenshots
- [ ] Before/after comparison visible
- [ ] Interaction states documented (if applicable)

## Examples

See `button-redesign-v1.4.7.md` for a complete example of visual documentation.

## Maintenance

- **Keep screenshots up-to-date** - Update when UI changes
- **Archive old versions** - Move to `docs/screenshots/archive/` if superseded
- **Clean up orphans** - Remove screenshots not referenced in docs
- **Compress large files** - Use PNG compression for files > 1MB

---

**Note**: UI changes without screenshots will NOT be approved in PR reviews.

**Last Updated**: 2026-02-02
**Maintainer**: HA Squid Proxy Team
