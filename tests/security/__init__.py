"""
Security test suite for Discord AI Bot Czech.

This package contains comprehensive security tests covering:
- Encryption and decryption security
- Key rotation and version management
- Credential migration security
- Access control and authentication
- Penetration testing scenarios

Usage:
    # Run all security tests
    python run_security_tests.py

    # Run individual test suites
    pytest test_encryption_security.py -v
    pytest test_key_rotation_security.py -v
    pytest test_migration_security.py -v
    pytest test_access_control_security.py -v
    pytest test_penetration_scenarios.py -v
"""

__version__ = "1.0.0"
__author__ = "Security Team"

# Test suite metadata
TEST_SUITES = [
    {
        "name": "Encryption Security",
        "file": "test_encryption_security.py",
        "description": "Tests for cryptographic implementation security",
        "test_count": 40
    },
    {
        "name": "Key Rotation Security",
        "file": "test_key_rotation_security.py",
        "description": "Tests for key rotation and version management",
        "test_count": 30
    },
    {
        "name": "Migration Security",
        "file": "test_migration_security.py",
        "description": "Tests for secure credential migration",
        "test_count": 25
    },
    {
        "name": "Access Control Security",
        "file": "test_access_control_security.py",
        "description": "Tests for authentication and authorization",
        "test_count": 50
    },
    {
        "name": "Penetration Testing",
        "file": "test_penetration_scenarios.py",
        "description": "Tests for common attack vectors",
        "test_count": 40
    }
]

# Security coverage areas
COVERAGE_AREAS = [
    "Cryptographic Security",
    "Authentication & Authorization",
    "Key Management",
    "Data Protection",
    "Attack Prevention",
    "Compliance"
]
