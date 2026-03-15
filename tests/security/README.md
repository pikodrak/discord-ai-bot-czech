# Security Test Suite

Comprehensive security testing for the Discord AI Bot Czech project, covering encryption, key rotation, credential migration, access control, and penetration testing scenarios.

## Overview

This security test suite provides extensive coverage of:

- **Encryption/Decryption Security**: Tests for AES-256-GCM encryption, key derivation, side-channel resistance
- **Key Rotation Security**: Tests for rotation strategies, zero-downtime rotation, version management
- **Migration Security**: Tests for secure credential migration, backup/recovery, rollback
- **Access Control Security**: Tests for JWT authentication, RBAC, session management
- **Penetration Testing**: Tests for brute force, token manipulation, credential stuffing, DoS resistance

## Test Files

### 1. `test_encryption_security.py`

Tests cryptographic implementation security:

- **Encryption Strength**: IND-CPA security, salt/nonce uniqueness, key derivation
- **Decryption Security**: Wrong key detection, corrupted data handling, GCM tag validation
- **Key Derivation**: PBKDF2 with 100,000 iterations, SHA-256 hash
- **Dictionary Encryption**: Selective key encryption, nested structure handling
- **Error Handling**: Information leakage prevention, generic error messages
- **Cryptographic Primitives**: AES-256-GCM, proper tag validation
- **Thread Safety**: Concurrent encryption operations

**Key Tests**:
- 40+ test cases covering encryption/decryption
- Timing attack resistance verification
- Unicode and large data handling
- Concurrent operation safety

### 2. `test_key_rotation_security.py`

Tests key rotation and version management:

- **Rotation Strategies**: IMMEDIATE, GRADUAL, VERSIONED
- **Zero-Downtime Rotation**: Credential availability during rotation
- **Version Management**: Metadata tracking, usage tracking, hash storage
- **Audit Trail**: Complete rotation history, status transitions
- **Rollback**: Safe rollback to previous versions
- **Cleanup**: Expired version removal, history retention
- **Concurrency**: Thread-safe rotation operations
- **Validation**: Callback-based validation and notifications

**Key Tests**:
- 30+ test cases covering rotation scenarios
- Concurrent rotation safety
- Audit trail integrity
- Version expiration handling

### 3. `test_migration_security.py`

Tests secure credential migration:

- **Data Integrity**: All credentials migrated, values preserved exactly
- **Backup/Recovery**: Backup before migration, recovery from backup
- **Rollback**: Restore original state on failure
- **Verification**: Migration verification, missing credential detection
- **Sensitive Data**: Memory clearing, log sanitization, temp file cleanup
- **Audit Trail**: Migration logging without plaintext values
- **Edge Cases**: Empty files, duplicates, malformed data
- **File Permissions**: Proper vault file permissions (0o600)

**Key Tests**:
- 25+ test cases covering migration scenarios
- Backup encryption verification
- Rollback on failure
- Audit trail without leaks

### 4. `test_access_control_security.py`

Tests authentication and authorization:

- **Password Security**: bcrypt hashing, salt uniqueness, timing attack resistance
- **JWT Security**: Signature verification, expiration enforcement, algorithm enforcement
- **RBAC**: Admin role enforcement, privilege escalation prevention
- **Session Management**: Token invalidation, concurrent sessions, timeout
- **Authorization**: 401/403 responses, permission enforcement
- **Password Generation**: Minimum length, complexity, uniqueness
- **Input Validation**: Username/email validation, SQL injection prevention, XSS prevention
- **CORS/CSRF**: Proper configuration

**Key Tests**:
- 50+ test cases covering access control
- Timing attack resistance on password verification
- Token tampering detection
- Role-based access enforcement

### 5. `test_penetration_scenarios.py`

Tests against common attack vectors:

- **Brute Force**: Rate limiting, exponential backoff, bcrypt work factor
- **Token Manipulation**: Signature forgery, algorithm substitution, replay attacks
- **Credential Stuffing**: Common password detection, complexity requirements
- **Session Hijacking**: Token binding, privilege change handling, secure cookies
- **Man-in-the-Middle**: HTTPS enforcement, certificate validation, TLS version
- **Information Disclosure**: Generic errors, stack trace hiding, debug mode
- **Denial of Service**: Payload limits, timeouts, connection limits
- **Cryptographic Attacks**: Side-channel resistance, rainbow table prevention
- **Compliance**: Password history, expiration, audit logging

**Key Tests**:
- 40+ test cases simulating attacks
- Real-world penetration scenarios
- Compliance requirements

### 6. `test_comprehensive_security_suite.py`

Advanced comprehensive security tests:

- **Advanced Encryption**: Maximum data size, binary data, nonce collision probability
- **Key Rotation Concurrency**: High-frequency rotation, concurrent access patterns
- **Migration Security Advanced**: Atomic operations, race conditions, corrupted sources
- **Access Control Advanced**: Privilege escalation, session fixation, concurrent logins
- **Advanced Penetration**: SQL injection, path traversal, command injection, XXE, deserialization
- **Compliance Validation**: GDPR, PCI DSS, SOC 2 requirements
- **Performance Under Security**: Throughput benchmarks, latency measurements, scalability

**Key Tests**:
- 60+ advanced test cases
- Performance benchmarking
- Compliance validation
- Real-world attack simulations

### 7. `test_security_integration.py`

End-to-end security integration tests:

- **Complete Credential Lifecycle**: Create → Store → Access → Rotate → Delete
- **Migration Workflow**: Full migration from .env to vault with verification
- **Authenticated Access**: Token-based credential access control
- **Admin-Only Operations**: Role-based rotation enforcement
- **Real-World Attacks**: Compromised database, stolen backups, insider threats
- **Security Failure Recovery**: Corruption recovery, rotation failure, migration rollback
- **Cross-Component Security**: Token-credential correlation, encryption-auth integration

**Key Tests**:
- 15+ integration scenarios
- End-to-end security workflows
- Attack simulation and recovery
- Component interaction validation

## Running the Tests

### Run All Security Tests

```bash
cd tests/security
python run_security_tests.py
```

This will:
1. Run all 5 test suites
2. Generate detailed reports
3. Provide vulnerability analysis
4. Output security recommendations

### Run Individual Test Suite

```bash
# Encryption tests
pytest test_encryption_security.py -v

# Key rotation tests
pytest test_key_rotation_security.py -v

# Migration tests
pytest test_migration_security.py -v

# Access control tests
pytest test_access_control_security.py -v

# Penetration tests
pytest test_penetration_scenarios.py -v
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html --cov-report=term tests/security/
```

## Test Reports

The test runner generates comprehensive reports in `security_reports/`:

### JSON Report

Machine-readable report with:
- Timestamp
- Test suite results
- Vulnerability summary
- Security recommendations

### Text Report

Human-readable report including:
- Test execution summary
- Detailed vulnerability list
- Prioritized recommendations
- Compliance checklist

### JUnit XML

Per-suite XML reports for CI/CD integration:
- `test_encryption_security_junit.xml`
- `test_key_rotation_security_junit.xml`
- `test_migration_security_junit.xml`
- `test_access_control_security_junit.xml`
- `test_penetration_scenarios_junit.xml`

## Security Test Coverage

### Cryptographic Security
- ✅ AES-256-GCM encryption
- ✅ PBKDF2 key derivation (100k iterations)
- ✅ Unique salts and nonces
- ✅ GCM authentication tag validation
- ✅ Side-channel attack resistance
- ✅ Timing attack resistance

### Authentication & Authorization
- ✅ bcrypt password hashing
- ✅ JWT token creation and verification
- ✅ Role-based access control (RBAC)
- ✅ Session management
- ✅ Token expiration enforcement
- ✅ Privilege escalation prevention

### Key Management
- ✅ Key rotation strategies (3 types)
- ✅ Zero-downtime rotation
- ✅ Version tracking and management
- ✅ Rotation audit trail
- ✅ Rollback capabilities
- ✅ Automatic cleanup

### Data Protection
- ✅ Encryption at rest
- ✅ Secure credential migration
- ✅ Backup and recovery
- ✅ Rollback on failure
- ✅ Proper file permissions
- ✅ No plaintext logging

### Attack Prevention
- ✅ Brute force protection
- ✅ Rate limiting concepts
- ✅ Token forgery prevention
- ✅ Replay attack prevention
- ✅ Credential stuffing protection
- ✅ Session hijacking prevention
- ✅ DoS resistance
- ✅ Information disclosure prevention

## Requirements

Install test dependencies:

```bash
pip install pytest pytest-cov cryptography python-jose[cryptography] bcrypt
```

## Environment Variables

Required for testing:

```bash
# Master encryption key (32+ characters recommended)
export MASTER_ENCRYPTION_KEY="your-secure-master-key-here"

# JWT secret key
export SECRET_KEY="your-jwt-secret-key-here"

# Optional: Token expiration (minutes)
export ACCESS_TOKEN_EXPIRE_MINUTES=60

# Optional: Environment (development/production)
export ENVIRONMENT=development
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Security Tests

on: [push, pull_request]

jobs:
  security-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run security tests
        env:
          MASTER_ENCRYPTION_KEY: ${{ secrets.MASTER_ENCRYPTION_KEY }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
        run: |
          cd tests/security
          python run_security_tests.py
      - name: Upload reports
        uses: actions/upload-artifact@v2
        with:
          name: security-reports
          path: tests/security/security_reports/
```

## Compliance Checklist

- [x] Encryption at rest (AES-256-GCM)
- [x] Key rotation support
- [x] Secure credential migration
- [x] Access control enforcement
- [x] Password hashing (bcrypt)
- [x] JWT authentication
- [ ] HTTPS enforcement (deployment config)
- [ ] Rate limiting (implementation required)
- [ ] Security event logging (implementation required)
- [ ] Token blacklist for logout (implementation required)
- [ ] Production database (currently in-memory)

## Known Limitations

### Current Implementation

1. **In-Memory Database**: User data not persisted, requires migration to SQL database
2. **No Token Blacklist**: JWT logout doesn't invalidate tokens (stateless)
3. **No Rate Limiting**: Authentication endpoints need rate limiting
4. **Hardcoded Defaults**: Remove default credentials before production
5. **CORS Wildcard**: Configure specific allowed origins
6. **No Security Logging**: Implement comprehensive audit logging

### Test Environment

1. **Mock Services**: Some tests use mocks instead of real services
2. **Timing Tests**: May have variance on different systems
3. **File Permissions**: Unix/Linux specific (0o600 checks)

## Security Recommendations

### Critical Priority

1. **Remove Hardcoded Credentials**: All default passwords and secret keys
2. **Implement Rate Limiting**: On authentication and API endpoints
3. **Add Token Blacklist**: Redis-based for logout functionality
4. **Replace In-Memory DB**: Use PostgreSQL/MySQL with proper persistence

### High Priority

5. **Configure CORS**: Whitelist specific origins, remove wildcard
6. **Add Security Logging**: SIEM-compatible event logging
7. **Account Lockout**: After N failed login attempts
8. **Environment Separation**: Different configs for dev/staging/prod

### Medium Priority

9. **Password Policies**: History, expiration, complexity enforcement
10. **HTTPS Enforcement**: Redirect HTTP to HTTPS, HSTS headers
11. **Security Headers**: CSP, X-Frame-Options, X-Content-Type-Options
12. **Input Sanitization**: Enhanced XSS and SQL injection prevention

### Low Priority

13. **Monitoring**: Security dashboards and alerts
14. **Penetration Testing**: Regular third-party security audits
15. **Compliance**: GDPR, SOC2, ISO27001 alignment
16. **Documentation**: Security policies and incident response plans

## Contributing

When adding new security tests:

1. Follow existing test structure
2. Include docstrings explaining what's tested
3. Group related tests in classes
4. Add both positive and negative test cases
5. Update this README with new test coverage
6. Update the test runner if adding new test files

## Support

For security issues:
- **DO NOT** create public GitHub issues for vulnerabilities
- Contact the security team directly
- Use responsible disclosure practices

For test questions:
- Create GitHub issues for test improvements
- Submit pull requests for new test coverage
- Update documentation with findings

## License

Same as main project license.
