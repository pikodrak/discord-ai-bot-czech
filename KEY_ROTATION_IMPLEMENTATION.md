# Key Rotation Implementation

Comprehensive key rotation system with automated policies, rotation history tracking, and zero-downtime rotation support.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Rotation Strategies](#rotation-strategies)
- [Automated Scheduling](#automated-scheduling)
- [API Reference](#api-reference)
- [Security Considerations](#security-considerations)
- [Best Practices](#best-practices)

## Overview

The key rotation system provides enterprise-grade credential rotation capabilities for the Discord AI Bot project. It integrates seamlessly with the existing credential vault and secrets manager to provide:

- **Zero-downtime rotation** - No service interruption during credential updates
- **Rotation history** - Complete audit trail of all rotation events
- **Automated policies** - Scheduled rotation based on configurable policies
- **Multiple strategies** - Immediate, gradual, or versioned rotation
- **Version management** - Track and manage multiple credential versions

## Features

### Core Capabilities

1. **Rotation History Tracking**
   - Complete audit trail of all rotations
   - Timestamps, reasons, and status tracking
   - Error logging and debugging information
   - Statistical analysis of rotation patterns

2. **Zero-Downtime Rotation**
   - Graceful transition between credential versions
   - Support for multiple active versions
   - Configurable transition periods
   - Validation callbacks for new credentials

3. **Automated Rotation Policies**
   - Scheduled rotation at configurable intervals
   - Custom rotation frequencies (daily, weekly, monthly, quarterly)
   - Pre and post-rotation hooks
   - Automatic value generation support

4. **Version Management**
   - Track multiple credential versions
   - Manual version deprecation
   - Automatic cleanup of expired versions
   - Usage statistics per version

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Rotation Scheduler                       │
│  - Automated policy enforcement                            │
│  - Scheduled rotation execution                            │
│  - Pre/post rotation hooks                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 Key Rotation Manager                        │
│  - Zero-downtime rotation logic                            │
│  - Version management                                       │
│  - Strategy implementation                                  │
└──────────┬────────────────────────┬─────────────────────────┘
           │                        │
           ▼                        ▼
┌──────────────────────┐  ┌─────────────────────────────────┐
│  Rotation History    │  │    Credential Vault             │
│  - Event tracking    │  │    - Encrypted storage          │
│  - Audit trail       │  │    - Access control             │
│  - Statistics        │  │    - Metadata management        │
└──────────────────────┘  └─────────────────────────────────┘
```

### File Structure

```
src/
├── rotation_history.py      # Rotation event tracking
├── key_rotation.py           # Zero-downtime rotation
├── rotation_scheduler.py     # Automated scheduling
├── credential_vault.py       # Existing credential storage
└── secrets_manager.py        # Existing encryption

tests/
└── test_key_rotation.py      # Comprehensive test suite

data/vault/
├── rotation_history/         # Rotation event logs
├── versions/                 # Credential version metadata
└── policies/                 # Rotation policy configurations
```

## Installation

No additional dependencies required beyond the existing project requirements:

```bash
# All dependencies already in requirements.txt
pip install -r requirements.txt
```

## Usage

### Basic Rotation

```python
from src.key_rotation import KeyRotationManager, RotationConfig, RotationStrategy
from src.rotation_history import RotationReason

# Initialize rotation manager
manager = KeyRotationManager()

# Configure rotation strategy
config = RotationConfig(
    strategy=RotationStrategy.GRADUAL,
    transition_period_hours=24
)
manager.set_rotation_config("DISCORD_BOT_TOKEN", config)

# Rotate credential
rotation_id = manager.rotate(
    credential_name="DISCORD_BOT_TOKEN",
    new_value="new-bot-token-value",
    reason=RotationReason.SCHEDULED,
    initiated_by="admin"
)

print(f"Rotation completed: {rotation_id}")
```

### Automated Rotation

```python
import asyncio
from src.rotation_scheduler import (
    RotationScheduler,
    RotationPolicy,
    RotationFrequency
)
from src.key_rotation import RotationConfig, RotationStrategy

# Initialize scheduler
scheduler = RotationScheduler(check_interval_seconds=3600)

# Define value generator for automatic rotation
def generate_new_token():
    import secrets
    return f"token_{secrets.token_urlsafe(32)}"

# Create rotation policy
policy = RotationPolicy(
    credential_name="API_KEY",
    enabled=True,
    frequency=RotationFrequency.MONTHLY,
    rotation_config=RotationConfig(
        strategy=RotationStrategy.GRADUAL,
        transition_period_hours=48
    ),
    value_generator=generate_new_token
)

# Add policy to scheduler
scheduler.add_policy(policy)

# Start automated rotation
async def run_scheduler():
    await scheduler.start()
    # Scheduler runs in background
    # Stop when done
    # await scheduler.stop()

asyncio.run(run_scheduler())
```

### Query Rotation History

```python
from src.rotation_history import RotationHistory, RotationStatus

# Initialize history
history = RotationHistory()

# Get recent rotations
recent = history.get_history("API_KEY", limit=10)

for event in recent:
    print(f"Rotation {event.rotation_id}:")
    print(f"  Status: {event.status.value}")
    print(f"  Reason: {event.reason.value}")
    print(f"  Time: {event.initiated_at}")

# Get statistics
stats = history.get_statistics("API_KEY")
print(f"Total rotations: {stats['total_rotations']}")
print(f"Success rate: {stats['successful_rotations']}/{stats['total_rotations']}")
print(f"Average duration: {stats['average_duration_seconds']}s")

# Get failed rotations
failed = history.get_failed_rotations()
for event in failed:
    print(f"Failed: {event.credential_name} - {event.error_message}")
```

### Version Management

```python
from src.key_rotation import KeyRotationManager

manager = KeyRotationManager()

# Get active versions
versions = manager.get_active_versions("API_KEY")
print(f"Active versions: {len(versions)}")

for version in versions:
    print(f"Version {version.version_id}:")
    print(f"  Created: {version.created_at}")
    print(f"  Primary: {version.is_primary}")
    print(f"  Usage count: {version.usage_count}")

# Deprecate specific version
manager.deprecate_version(
    "API_KEY",
    version_id="v_abc123",
    graceful_period_hours=24
)

# Get rotation status
status = manager.get_rotation_status("API_KEY")
print(f"Primary version age: {status['primary_version_age_days']} days")
print(f"Total versions: {status['total_versions']}")
```

## Rotation Strategies

### Immediate Rotation

Old credential is immediately invalidated when new one is set.

```python
config = RotationConfig(strategy=RotationStrategy.IMMEDIATE)
```

**Use cases:**
- Compromised credentials requiring immediate replacement
- Development/testing environments
- Non-critical services

**Considerations:**
- May cause brief service interruption
- Ensure all services can quickly pick up new credential

### Gradual Rotation

Both old and new credentials remain valid during transition period.

```python
config = RotationConfig(
    strategy=RotationStrategy.GRADUAL,
    transition_period_hours=48  # 48-hour transition
)
```

**Use cases:**
- Production services requiring zero-downtime
- Distributed systems with gradual rollout
- APIs with caching

**Considerations:**
- Provides time for all services to update
- Requires monitoring to ensure transition completes
- Both credentials must remain valid during period

### Versioned Rotation

Multiple credential versions tracked, manual deprecation required.

```python
config = RotationConfig(
    strategy=RotationStrategy.VERSIONED,
    max_active_versions=3
)
```

**Use cases:**
- Multiple services using different credential versions
- Complex migration scenarios
- Testing new credentials before full rollout

**Considerations:**
- Manual cleanup required
- Useful for canary deployments
- Monitor usage per version

## Automated Scheduling

### Rotation Frequencies

```python
from src.rotation_scheduler import RotationFrequency

# Built-in frequencies
RotationFrequency.DAILY         # Every 24 hours
RotationFrequency.WEEKLY        # Every 7 days
RotationFrequency.MONTHLY       # Every 30 days
RotationFrequency.QUARTERLY     # Every 90 days

# Custom frequency
policy = RotationPolicy(
    credential_name="KEY",
    frequency=RotationFrequency.CUSTOM_DAYS,
    custom_days=45  # Every 45 days
)
```

### Pre/Post Rotation Hooks

```python
def pre_rotation_check(credential_name: str) -> bool:
    """Called before rotation starts."""
    # Verify system is ready for rotation
    if not is_system_healthy():
        return False  # Skip rotation

    # Log pre-rotation state
    log_system_state()
    return True  # Proceed with rotation

def post_rotation_notify(credential_name: str, rotation_id: str):
    """Called after successful rotation."""
    # Send notifications
    send_slack_message(f"Rotated {credential_name}: {rotation_id}")

    # Update monitoring
    update_dashboard(credential_name, rotation_id)

policy = RotationPolicy(
    credential_name="API_KEY",
    pre_rotation_hook=pre_rotation_check,
    post_rotation_hook=post_rotation_notify,
    value_generator=generate_new_value
)
```

### Monitoring Scheduled Rotations

```python
scheduler = RotationScheduler()

# Get upcoming rotations
next_rotations = scheduler.get_next_rotations(limit=5)
for cred_name, rotation_time in next_rotations:
    print(f"{cred_name}: {rotation_time}")

# Get scheduler status
status = scheduler.get_status()
print(f"Running: {status['running']}")
print(f"Enabled policies: {status['enabled_policies']}")
print(f"Due rotations: {status['due_rotations']}")

# Force immediate rotation
await scheduler.rotate_now("API_KEY")
```

## API Reference

### RotationHistory

Track and query rotation events.

```python
class RotationHistory:
    def add_event(self, event: RotationEvent) -> None
    def update_event(
        self,
        credential_name: str,
        rotation_id: str,
        status: Optional[RotationStatus] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> bool

    def get_history(
        self,
        credential_name: str,
        limit: Optional[int] = None,
        status_filter: Optional[RotationStatus] = None
    ) -> List[RotationEvent]

    def get_statistics(
        self,
        credential_name: str
    ) -> Dict[str, Any]
```

### KeyRotationManager

Manage credential rotation with zero-downtime.

```python
class KeyRotationManager:
    def rotate(
        self,
        credential_name: str,
        new_value: str,
        reason: RotationReason = RotationReason.MANUAL,
        initiated_by: Optional[str] = None
    ) -> str  # Returns rotation_id

    def get_credential(
        self,
        credential_name: str,
        version_id: Optional[str] = None
    ) -> Optional[str]

    def get_active_versions(
        self,
        credential_name: str
    ) -> List[CredentialVersion]

    def deprecate_version(
        self,
        credential_name: str,
        version_id: str,
        graceful_period_hours: int = 0
    ) -> bool

    def get_rotation_status(
        self,
        credential_name: str
    ) -> Dict[str, Any]
```

### RotationScheduler

Automate credential rotation with policies.

```python
class RotationScheduler:
    def add_policy(self, policy: RotationPolicy) -> None
    def remove_policy(self, credential_name: str) -> bool
    def enable_policy(self, credential_name: str) -> bool
    def disable_policy(self, credential_name: str) -> bool

    async def start(self) -> None
    async def stop(self) -> None

    async def rotate_now(self, credential_name: str) -> bool

    def get_next_rotations(
        self,
        limit: int = 10
    ) -> List[Tuple[str, datetime]]

    def get_status(self) -> Dict[str, Any]
```

## Security Considerations

### Encryption

All credential values are encrypted using:
- **AES-256-GCM** authenticated encryption
- **PBKDF2** key derivation (100,000 iterations)
- Unique salt and nonce per encryption operation

### File Permissions

Rotation system maintains strict file permissions:
- History directory: `0o700` (rwx------)
- Version files: `0o600` (rw-------)
- Policy files: `0o600` (rw-------)

### Audit Trail

Complete audit trail includes:
- Who initiated rotation
- When rotation occurred
- Why rotation was performed
- Success/failure status
- Error messages for failures
- Duration of rotation operation

### Value Hashing

Credential values are hashed (SHA-256) for:
- Tracking value changes without storing plaintext
- Verifying rotation success
- Statistical analysis

Hashes are stored in:
- Rotation events
- Version metadata

**Note:** Actual credential values are never logged or stored in plaintext in history/metadata.

## Best Practices

### 1. Choose Appropriate Strategy

```python
# Production services - use gradual rotation
production_config = RotationConfig(
    strategy=RotationStrategy.GRADUAL,
    transition_period_hours=48
)

# Development/testing - use immediate rotation
dev_config = RotationConfig(
    strategy=RotationStrategy.IMMEDIATE
)

# Complex migrations - use versioned rotation
migration_config = RotationConfig(
    strategy=RotationStrategy.VERSIONED,
    max_active_versions=3
)
```

### 2. Set Appropriate Rotation Frequency

Based on credential type:

```python
# API Keys - rotate quarterly
api_key_policy = RotationPolicy(
    credential_name="API_KEY",
    frequency=RotationFrequency.QUARTERLY
)

# Passwords - rotate monthly
password_policy = RotationPolicy(
    credential_name="ADMIN_PASSWORD",
    frequency=RotationFrequency.MONTHLY
)

# Tokens - rotate weekly
token_policy = RotationPolicy(
    credential_name="ACCESS_TOKEN",
    frequency=RotationFrequency.WEEKLY
)
```

### 3. Implement Validation

```python
def validate_api_key(value: str) -> bool:
    """Validate new API key format."""
    # Check minimum length
    if len(value) < 32:
        return False

    # Check format (example: must start with 'key_')
    if not value.startswith('key_'):
        return False

    # Test with API (if possible)
    try:
        test_api_call(value)
        return True
    except:
        return False

config = RotationConfig(
    strategy=RotationStrategy.GRADUAL,
    validation_callback=validate_api_key
)
```

### 4. Monitor Rotation Health

```python
from src.rotation_history import RotationHistory

history = RotationHistory()

# Regular health checks
def check_rotation_health():
    # Check for failed rotations
    failed = history.get_failed_rotations()
    if failed:
        alert_team(f"Failed rotations detected: {len(failed)}")

    # Check rotation age for critical credentials
    for cred_name in CRITICAL_CREDENTIALS:
        stats = history.get_statistics(cred_name)
        if stats['last_rotation']:
            last_rotation = datetime.fromisoformat(stats['last_rotation'])
            age_days = (datetime.utcnow() - last_rotation).days

            if age_days > MAX_ROTATION_AGE_DAYS:
                alert_team(f"{cred_name} not rotated in {age_days} days")

# Run health check regularly
schedule_task(check_rotation_health, interval_hours=24)
```

### 5. Clean Up Old History

```python
from src.rotation_history import RotationHistory

history = RotationHistory()

# Keep only recent events to prevent unbounded growth
def cleanup_rotation_history():
    for credential_name in get_all_credentials():
        removed = history.cleanup_old_events(
            credential_name,
            keep_count=100  # Keep 100 most recent events
        )
        if removed > 0:
            logger.info(f"Cleaned up {removed} old events for {credential_name}")

# Run cleanup monthly
schedule_task(cleanup_rotation_history, interval_days=30)
```

### 6. Test Rotation Before Production

```python
# Test rotation in staging environment
def test_rotation_flow():
    manager = KeyRotationManager()

    # Set test credential
    manager.vault.set_credential(
        name="TEST_API_KEY",
        value="test_value_1",
        credential_type=CredentialType.API_KEY
    )

    # Configure gradual rotation
    config = RotationConfig(
        strategy=RotationStrategy.GRADUAL,
        transition_period_hours=1  # Short for testing
    )
    manager.set_rotation_config("TEST_API_KEY", config)

    # Perform rotation
    rotation_id = manager.rotate(
        credential_name="TEST_API_KEY",
        new_value="test_value_2",
        reason=RotationReason.MANUAL
    )

    # Verify both versions are active
    versions = manager.get_active_versions("TEST_API_KEY")
    assert len(versions) == 2, "Both versions should be active"

    # Verify primary version
    primary_value = manager.get_credential("TEST_API_KEY")
    assert primary_value == "test_value_2", "New value should be primary"

    print("✓ Rotation test passed")

# Run before deploying to production
test_rotation_flow()
```

### 7. Document Rotation Procedures

Create runbooks for:
- Emergency manual rotation
- Rollback procedures
- Troubleshooting failed rotations
- Verifying rotation success

Example emergency rotation:

```python
def emergency_rotation(credential_name: str, new_value: str):
    """Emergency rotation for compromised credentials."""
    manager = KeyRotationManager()

    # Use immediate strategy for compromised credentials
    config = RotationConfig(strategy=RotationStrategy.IMMEDIATE)
    manager.set_rotation_config(credential_name, config)

    # Rotate immediately
    rotation_id = manager.rotate(
        credential_name=credential_name,
        new_value=new_value,
        reason=RotationReason.COMPROMISED,
        initiated_by="security_team"
    )

    # Verify rotation
    status = manager.get_rotation_status(credential_name)
    if status['latest_rotation_status'] != 'completed':
        raise Exception("Emergency rotation failed!")

    # Alert team
    send_alert(f"Emergency rotation completed: {rotation_id}")

    return rotation_id
```

## Troubleshooting

### Rotation Failures

Check rotation history for errors:

```python
history = RotationHistory()
failed = history.get_failed_rotations("API_KEY")

for event in failed:
    print(f"Failed rotation {event.rotation_id}")
    print(f"Error: {event.error_message}")
    print(f"Time: {event.initiated_at}")
```

### Version Cleanup Issues

Manually clean up expired versions:

```python
manager = KeyRotationManager()

# Clean all expired versions
results = manager.cleanup_all_expired()

for cred_name, removed_count in results.items():
    print(f"Removed {removed_count} expired versions from {cred_name}")
```

### Scheduler Not Running

Check scheduler status:

```python
scheduler = RotationScheduler()
status = scheduler.get_status()

if not status['running']:
    print("Scheduler not running!")
    await scheduler.start()
```

## License

Part of the Discord AI Bot project. See main project LICENSE for details.
