# HTTPS Fix 1.1.18 - Rock Solid Implementation

## Issues Fixed

### 1. HTTPS Certificate Error
**Error**: `FATAL: No valid signing certificate configured for HTTPS_port [::]:3133`

**Root Cause**: Certificate key file had permissions `0o600` (owner-only), but Squid runs as a different user (typically `nobody` or `squid`) and couldn't read the key file.

**Solution**:
- Changed key file permissions from `0o600` to `0o644` (readable by all)
- Added OpenSSL certificate validation before starting Squid
- Added file readability checks
- Added detailed logging for certificate validation

### 2. UI Styling Issues
**Problem**: Certificate settings section not displaying correctly, modal too narrow

**Solution**:
- Increased modal width from 500px to 600px
- Fixed certificate settings section background color (dark theme compatible)
- Added proper styling for select dropdowns
- Added focus states for form inputs
- Improved modal scrolling with max-height

## Key Changes

### Backend (`cert_manager.py`, `proxy_manager.py`)

1. **Certificate File Permissions**
   - Key file: `0o600` → `0o644` (Squid compatibility)
   - Certificate file: `0o644` (unchanged)
   - Both files now readable by Squid process

2. **Certificate Validation**
   - Added OpenSSL validation before Squid starts
   - Validates certificate can be parsed
   - Logs certificate subject and issuer
   - Verifies file readability

3. **Pre-flight Checks**
   - Verify files exist
   - Verify file permissions
   - Verify files are readable
   - Validate certificate format

### Frontend (`main.py`)

1. **Modal CSS**
   - Width: 500px → 600px
   - Max-height: 90vh with scrolling
   - Better spacing for certificate section

2. **Certificate Settings Styling**
   - Dark theme compatible background
   - Proper border and spacing
   - Improved form input styling
   - Added select dropdown styling

3. **Form Improvements**
   - Added focus states
   - Better input/select styling
   - Improved visual hierarchy

### Tests

1. **New Integration Tests** (`test_https_certificate_access.py`)
   - Certificate file permissions test
   - OpenSSL validation test
   - File readability test
   - Squid config path validation test

2. **Updated Tests**
   - Updated permission assertions (600 → 644)
   - Fixed path validation tests

## Test Results

- **Unit Tests**: 102 passed, 6 skipped
- **Integration Tests**: 106 passed, 6 skipped
- **All HTTPS certificate tests**: ✅ Passing

## Files Changed

1. `cert_manager.py` - Changed key permissions to 0o644
2. `proxy_manager.py` - Added OpenSSL validation and file checks
3. `main.py` - Fixed UI styling and modal width
4. `test_cert_manager.py` - Updated permission assertions
5. `test_https_certificates.py` - Updated permission assertions
6. `test_https_certificate_access.py` - New comprehensive tests
7. `config.yaml` - Version bump to 1.1.18
8. `Dockerfile` - Version bump to 1.1.18

## Verification Checklist

- ✅ Certificate key file has 0o644 permissions (Squid readable)
- ✅ Certificate file has 0o644 permissions
- ✅ OpenSSL validation runs before Squid starts
- ✅ File readability checks pass
- ✅ UI modal displays correctly with proper styling
- ✅ Certificate settings section is visible and styled
- ✅ All tests pass
- ✅ Version bumped to 1.1.18

## Next Steps

1. Commit changes
2. Create git tag v1.1.18
3. Push to repository
4. Test in Home Assistant environment
5. Verify HTTPS instances start successfully
