# HTTPS Enable Fix - Version 1.1.16

## Issue
Enabling HTTPS option from the UI was not working. Error:
```
FATAL: No valid signing certificate configured for HTTPS_port [::]:3130
```

## Root Causes

1. **Wrong Certificate File Permissions**: Certificate file was set to directory permissions (0o755) instead of file permissions (0o644)
2. **Missing Certificate Verification**: No verification that certificates exist before starting Squid
3. **Timing Issue**: No delay after certificate generation, files might not be fully written
4. **No Empty File Check**: Didn't verify certificate files have content

## Fixes Applied

### 1. Fixed Certificate Permissions (`cert_manager.py`)
- Changed `PERM_DIRECTORY` to `PERM_CERTIFICATE = 0o644` for certificate files
- Certificate files now have correct readable permissions (0o644)
- Private key files remain restricted (0o600)

### 2. Added Certificate Verification (`proxy_manager.py`)
- Verify certificates exist before starting instance
- Check certificate file sizes (must be > 0)
- Fix permissions if incorrect
- Added error messages with file paths

### 3. Improved Update Flow (`update_instance`)
- Ensure certificate directory exists with proper permissions
- Generate certificates when enabling HTTPS
- Verify certificates exist and are valid before restart
- Added delay after certificate generation to ensure files are written
- Better error handling with detailed messages

### 4. Enhanced Start Instance (`start_instance`)
- Verify HTTPS certificates exist before starting
- Check and fix certificate permissions
- Provide clear error messages if certificates are missing

## Changes Made

### `cert_manager.py`
- Added `PERM_CERTIFICATE = 0o644` constant
- Fixed certificate file permissions from `PERM_DIRECTORY` to `PERM_CERTIFICATE`

### `proxy_manager.py`
- Added certificate verification in `create_instance`
- Added certificate verification in `update_instance`
- Added certificate verification in `start_instance`
- Added delays after certificate generation
- Added file size verification
- Improved error messages

## Testing

To test the fix:
1. Create a new instance with HTTPS enabled from UI
2. Update an existing instance to enable HTTPS
3. Verify certificates are created in `/data/squid_proxy_manager/certs/{instance_name}/`
4. Verify Squid starts successfully with HTTPS enabled

## Version
Bumped to **1.1.16** for this bug fix.
