# HTTPS Feature - Comprehensive Test Plan

## Overview

This document defines the test plan for HTTPS functionality with 100% coverage across unit, integration, and E2E (UI) tests.

## Test Scope

### In Scope
- Certificate generation (server certificates)
- Certificate file permissions
- Certificate validation
- HTTPS instance creation
- HTTPS enable on existing instance
- Certificate regeneration
- Certificate parameters customization
- UI for HTTPS settings
- Squid startup with HTTPS
- HTTPS proxy functionality

### Out of Scope
- CA certificate functionality (we generate server certificates only)
- Certificate revocation
- Client certificate authentication

## Test Cases

### Unit Tests (test_cert_manager.py)

| ID | Test Case | Expected Result | Status |
|----|-----------|-----------------|--------|
| U-HTTPS-01 | Generate certificate creates server cert (not CA) | BasicConstraints.ca = False | ✅ |
| U-HTTPS-02 | Certificate has correct KeyUsage | digital_signature=True, key_cert_sign=False | ✅ |
| U-HTTPS-03 | Certificate has ExtendedKeyUsage SERVER_AUTH | ExtendedKeyUsageOID.SERVER_AUTH present | ✅ |
| U-HTTPS-04 | Certificate file has 0o644 permissions | oct(mode)[-3:] == "644" | ✅ |
| U-HTTPS-05 | Key file has 0o644 permissions | oct(mode)[-3:] == "644" | ✅ |
| U-HTTPS-06 | Certificate is valid PEM format | Can load with x509.load_pem_x509_certificate | ✅ |
| U-HTTPS-07 | Custom validity days applied | Certificate valid for specified days | ✅ |
| U-HTTPS-08 | Custom key size applied | Key generated with specified size | ✅ |
| U-HTTPS-09 | Custom common name applied | Subject CN matches parameter | ✅ |
| U-HTTPS-10 | Custom country applied | Subject Country matches parameter | ✅ |
| U-HTTPS-11 | Custom organization applied | Subject Org matches parameter | ✅ |

### Integration Tests (test_https_certificates.py, test_https_certificate_access.py)

| ID | Test Case | Expected Result | Status |
|----|-----------|-----------------|--------|
| I-HTTPS-01 | Create HTTPS instance generates certificates | cert_file.exists() and key_file.exists() | ✅ |
| I-HTTPS-02 | Certificate file permissions are 0o644 | oct(mode)[-3:] == "644" | ✅ |
| I-HTTPS-03 | Key file permissions are 0o644 | oct(mode)[-3:] == "644" | ✅ |
| I-HTTPS-04 | Certificate validates with OpenSSL | openssl x509 -in cert -noout -text returns 0 | ✅ |
| I-HTTPS-05 | Certificate files are readable | open(file, "r").read() succeeds | ✅ |
| I-HTTPS-06 | Squid config has correct HTTPS paths | tls-cert= and tls-key= present | ✅ |
| I-HTTPS-07 | Paths in config are absolute | path.startswith("/") | ✅ |
| I-HTTPS-08 | Enable HTTPS on HTTP instance | Certificates generated, config updated | ✅ |
| I-HTTPS-09 | Certificate parameters applied | Subject has custom CN/Country/Org | ✅ |
| I-HTTPS-10 | Certificate regeneration | New certificates generated | ⚠️ |
| I-HTTPS-11 | Instance starts with HTTPS | instance["running"] == True | ⚠️ |

### E2E Tests (test_https_ui.py)

| ID | Test Case | Expected Result | Status |
|----|-----------|-----------------|--------|
| E-HTTPS-01 | Create HTTPS instance via UI | Instance created with https_enabled=True | ✅ |
| E-HTTPS-02 | Certificate settings visible when HTTPS checked | newCertSettings visible | ✅ |
| E-HTTPS-03 | Certificate parameters sent to API | cert_params in request body | ✅ |
| E-HTTPS-04 | Progress indicator shows during generation | newCertProgress visible | ⚠️ |
| E-HTTPS-05 | HTTPS instance starts from UI | Status shows "Running" | ✅ |
| E-HTTPS-06 | Enable HTTPS on existing instance via Settings | Settings modal, check HTTPS, save | ✅ |
| E-HTTPS-07 | Certificate settings in Settings modal | editCertSettings visible | ✅ |
| E-HTTPS-08 | Regenerate certificates button works | Certs regenerated, instance restarts | ✅ |
| E-HTTPS-09 | Test connectivity works for HTTPS instance | Test returns success | ⚠️ |
| E-HTTPS-10 | Delete HTTPS instance via UI | Instance deleted, certs cleaned up | ✅ |

### Squid Process Tests (test_process_integration.py)

| ID | Test Case | Expected Result | Status |
|----|-----------|-----------------|--------|
| P-HTTPS-01 | Squid process starts with HTTPS config | Process running, no errors | ⚠️ |
| P-HTTPS-02 | Squid can read certificate files | No "Failed to acquire TLS" errors | ⚠️ |
| P-HTTPS-03 | HTTPS proxy accepts connections | curl --proxy https:// succeeds | ⚠️ |
| P-HTTPS-04 | HTTPS proxy authenticates users | 407 then 200 with credentials | ⚠️ |

## Legend

- ✅ Implemented and passing
- ⚠️ Partially implemented or needs verification
- ❌ Not implemented

## Implementation Priority

### Phase 1: Critical (Must Have)
1. E-HTTPS-01: Create HTTPS instance via UI
2. E-HTTPS-05: HTTPS instance starts from UI
3. E-HTTPS-10: Delete HTTPS instance via UI
4. P-HTTPS-01: Squid process starts with HTTPS

### Phase 2: Important (Should Have)
5. E-HTTPS-02: Certificate settings visibility
6. E-HTTPS-06: Enable HTTPS on existing instance
7. P-HTTPS-02: Squid can read certificates

### Phase 3: Nice to Have
8. E-HTTPS-03, E-HTTPS-04: Progress indicators
9. E-HTTPS-07, E-HTTPS-08: Certificate regeneration UI
10. E-HTTPS-09: Test connectivity for HTTPS

## Test Environment Requirements

### For Unit Tests
- Python 3.10+
- cryptography library
- pytest-asyncio

### For Integration Tests
- All unit test requirements
- aiohttp
- OpenSSL CLI available

### For E2E Tests
- All integration test requirements
- Playwright
- Docker (for Squid process)
- Network access for proxy testing

### For Process Tests
- All E2E requirements
- Real Squid binary
- Port binding capability
- Network access

## Running Tests

```bash
# All tests
./run_tests.sh

# HTTPS-specific tests
./run_tests.sh tests/unit/test_cert_manager.py -v
./run_tests.sh tests/integration/test_https_certificates.py tests/integration/test_https_certificate_access.py -v
./run_tests.sh tests/e2e/test_full_flow.py -k "https" -v

# With coverage
./run_tests.sh --cov=squid_proxy_manager --cov-report=html
```

## Success Criteria

- All unit tests pass (U-HTTPS-01 to U-HTTPS-11)
- All integration tests pass (I-HTTPS-01 to I-HTTPS-11)
- All E2E tests pass (E-HTTPS-01 to E-HTTPS-10)
- Test coverage > 80% for HTTPS-related code
- No HTTPS-related bugs in production
