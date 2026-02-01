# Release Plan v1.4.4: Record Workflows Finalization

**Status**: ⏳ In Progress
**Version**: 1.4.4 (from 1.4.3)
**Planned Date**: January 31, 2026
**Git Tag**: `v1.4.4`

---

## 🎯 Objective

Finalize the recording pipeline so a single script run manages addon lifecycle, recording, and GIF output with consistent Docker execution.

## ✅ Planned Changes

1. Fix `record_workflows.sh` Docker checks and environment defaults.
2. Add OS-aware Docker addon URL handling (macOS uses `host.docker.internal`, Linux uses host network).
3. Clean previous GIFs before recording to avoid stale outputs.
4. Run recordings via `docker compose run` to avoid image-name mismatches.
5. Update pre-release README to reflect the unified script flow.

## 📦 Deliverables

- `pre_release_scripts/record_workflows.sh`
- `pre_release_scripts/README.md`
- Generated GIFs in `docs/gifs/`

## ✅ Verification

- Run `./record_workflows.sh`
- Verify:
  - `docs/gifs/00-add-first-proxy.gif`
  - `docs/gifs/01-add-https-proxy.gif`

## 🔗 Notes

- Docker-first workflow only; no local tool installs.
- No new dependencies introduced.
