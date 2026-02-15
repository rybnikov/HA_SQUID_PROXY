# Git Hooks

This directory contains shared git hooks for the project.

## Setup

To use these hooks, run:

```bash
git config core.hooksPath .githooks
```

Or add this to your local git config:

```bash
git config --local core.hooksPath .githooks
```

## Available Hooks

### pre-push

Runs before pushing code to remote:
- ✅ Linting checks (black, ruff, mypy, bandit)
- ✅ Frontend unit tests
- ✅ Backend unit + integration tests
- ✅ Sanity checks for critical files

**Auto-fix behavior:**
If black or other formatters auto-fix files during the pre-push hook, those changes are automatically staged and amended to the current commit. This prevents the "linting passed locally but failed in CI" issue.

## Troubleshooting

If you see `✗ Linting failed!`, run:
```bash
docker compose -f docker-compose.test.yaml --profile lint up --build
```

Then commit the formatting fixes and try pushing again.
