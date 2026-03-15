#!/usr/bin/env python3
"""
Command-line utility for managing secure credentials.

Usage:
    python scripts/manage_credentials.py generate-key
    python scripts/manage_credentials.py set CREDENTIAL_NAME value
    python scripts/manage_credentials.py get CREDENTIAL_NAME
    python scripts/manage_credentials.py list
    python scripts/manage_credentials.py rotate CREDENTIAL_NAME new_value
    python scripts/manage_credentials.py delete CREDENTIAL_NAME
    python scripts/manage_credentials.py check-rotation
    python scripts/manage_credentials.py health
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.credential_vault import (
    CredentialVault,
    CredentialType,
    get_credential_vault
)
from src.secrets_manager import generate_master_key
from src.credential_loader import check_credential_health


def print_help():
    """Print usage help."""
    print("""
Credential Management Utility

Commands:
  generate-key                  Generate a new master encryption key
  set NAME VALUE [TYPE]        Store a credential (types: api_key, password, token, secret)
  get NAME                     Retrieve a credential
  list [TYPE]                  List all credentials or filter by type
  rotate NAME NEW_VALUE        Rotate a credential with new value
  delete NAME                  Delete a credential
  check-rotation               Check which credentials need rotation
  health                       Check credential system health
  export                       Export credential structure (no values)

Examples:
  python scripts/manage_credentials.py generate-key
  python scripts/manage_credentials.py set DISCORD_BOT_TOKEN "your-token" token
  python scripts/manage_credentials.py get DISCORD_BOT_TOKEN
  python scripts/manage_credentials.py list api_key
  python scripts/manage_credentials.py rotate ADMIN_PASSWORD "new-secure-password"
  python scripts/manage_credentials.py health
""")


def cmd_generate_key():
    """Generate new master encryption key."""
    key = generate_master_key()
    print("Generated master encryption key:")
    print()
    print(f"MASTER_ENCRYPTION_KEY={key}")
    print()
    print("IMPORTANT:")
    print("1. Add this to your .env file or set as environment variable")
    print("2. Store this key securely - you cannot decrypt credentials without it")
    print("3. Never commit this key to version control")
    print("4. Use different keys for development, staging, and production")


def cmd_set(name: str, value: str, cred_type: str = "secret"):
    """Store a credential."""
    vault = get_credential_vault()

    # Parse credential type
    try:
        credential_type = CredentialType(cred_type.lower())
    except ValueError:
        print(f"Error: Invalid credential type '{cred_type}'")
        print(f"Valid types: {', '.join(t.value for t in CredentialType)}")
        sys.exit(1)

    # Set rotation days based on type
    rotation_days = None
    if credential_type == CredentialType.PASSWORD:
        rotation_days = 90  # Rotate passwords every 90 days
    elif credential_type in (CredentialType.API_KEY, CredentialType.TOKEN):
        rotation_days = 180  # Rotate API keys/tokens every 180 days

    try:
        vault.set_credential(
            name=name,
            value=value,
            credential_type=credential_type,
            rotation_days=rotation_days,
            force=True  # Allow overwrite
        )
        print(f"✓ Stored credential: {name}")
        print(f"  Type: {credential_type.value}")
        if rotation_days:
            print(f"  Rotation: Every {rotation_days} days")
    except Exception as e:
        print(f"Error storing credential: {e}")
        sys.exit(1)


def cmd_get(name: str):
    """Retrieve a credential."""
    vault = get_credential_vault()

    value = vault.get_credential(name, env_var_override=True)

    if value:
        print(f"Credential: {name}")
        print(f"Value: {value}")

        # Show metadata if available
        meta = vault.get_metadata(name)
        if meta:
            print(f"Type: {meta.credential_type.value}")
            print(f"Accessed: {meta.access_count} times")
            if meta.last_accessed:
                print(f"Last access: {meta.last_accessed.isoformat()}")
            if meta.rotation_days:
                print(f"Rotation policy: Every {meta.rotation_days} days")
                if meta.needs_rotation():
                    print("⚠ WARNING: This credential needs rotation!")
    else:
        print(f"Credential '{name}' not found")
        print("Tip: Use 'list' command to see available credentials")
        sys.exit(1)


def cmd_list(cred_type: str = None):
    """List all credentials."""
    vault = get_credential_vault()

    # Parse credential type filter
    credential_type = None
    if cred_type:
        try:
            credential_type = CredentialType(cred_type.lower())
        except ValueError:
            print(f"Error: Invalid credential type '{cred_type}'")
            print(f"Valid types: {', '.join(t.value for t in CredentialType)}")
            sys.exit(1)

    credentials = vault.list_credentials(credential_type)

    if not credentials:
        if credential_type:
            print(f"No credentials of type '{credential_type.value}' found")
        else:
            print("No credentials stored in vault")
        return

    print(f"Stored credentials ({len(credentials)}):")
    print()

    for name in credentials:
        meta = vault.get_metadata(name)
        if meta:
            rotation_marker = " ⚠ NEEDS ROTATION" if meta.needs_rotation() else ""
            print(f"  • {name}")
            print(f"    Type: {meta.credential_type.value}{rotation_marker}")
            print(f"    Created: {meta.created_at.strftime('%Y-%m-%d')}")
            if meta.rotation_days:
                print(f"    Rotation: Every {meta.rotation_days} days")
            print()


def cmd_rotate(name: str, new_value: str):
    """Rotate a credential."""
    vault = get_credential_vault()

    try:
        vault.rotate_credential(name, new_value)
        print(f"✓ Rotated credential: {name}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error rotating credential: {e}")
        sys.exit(1)


def cmd_delete(name: str):
    """Delete a credential."""
    vault = get_credential_vault()

    # Confirm deletion
    response = input(f"Delete credential '{name}'? (yes/no): ")
    if response.lower() not in ('yes', 'y'):
        print("Cancelled")
        return

    if vault.delete_credential(name):
        print(f"✓ Deleted credential: {name}")
    else:
        print(f"Credential '{name}' not found")


def cmd_check_rotation():
    """Check which credentials need rotation."""
    vault = get_credential_vault()

    credentials = vault.credentials_needing_rotation()

    if not credentials:
        print("✓ No credentials need rotation")
        return

    print(f"⚠ {len(credentials)} credential(s) need rotation:")
    print()

    for name in credentials:
        meta = vault.get_metadata(name)
        if meta:
            last_rotation = meta.last_rotated or meta.created_at
            days_old = (meta.created_at.utcnow() - last_rotation).days

            print(f"  • {name}")
            print(f"    Type: {meta.credential_type.value}")
            print(f"    Last rotated: {last_rotation.strftime('%Y-%m-%d')} ({days_old} days ago)")
            print(f"    Policy: Rotate every {meta.rotation_days} days")
            print()


def cmd_health():
    """Check credential system health."""
    health = check_credential_health()

    print("Credential System Health Check")
    print("=" * 50)
    print()

    status_icon = "✓" if health["status"] == "healthy" else "⚠"
    print(f"Status: {status_icon} {health['status'].upper()}")
    print()

    print(f"Total credentials configured: {health['total_credentials']}")
    print(f"Successfully loaded: {health['loaded_credentials']}")
    print(f"Missing: {health['missing_credentials']}")
    print(f"Coverage: {health['coverage_percent']}%")
    print()

    if health.get("missing_list"):
        print("Missing credentials:")
        for name in health["missing_list"]:
            print(f"  • {name}")
        print()

    print(f"Vault credentials: {health['vault_credentials']}")

    if health.get("needs_rotation"):
        print(f"⚠ Needs rotation: {len(health['needs_rotation'])}")
        for name in health["needs_rotation"]:
            print(f"  • {name}")
    else:
        print("✓ No credentials need rotation")


def cmd_export():
    """Export credential structure."""
    vault = get_credential_vault()

    output = vault.export_for_env()
    print("Credential structure (for .env file):")
    print()
    print(output)
    print()
    print("Note: Actual values are encrypted in vault")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    command = sys.argv[1].lower()

    try:
        if command == "generate-key":
            cmd_generate_key()

        elif command == "set":
            if len(sys.argv) < 4:
                print("Error: set command requires NAME and VALUE")
                print("Usage: set NAME VALUE [TYPE]")
                sys.exit(1)
            name = sys.argv[2]
            value = sys.argv[3]
            cred_type = sys.argv[4] if len(sys.argv) > 4 else "secret"
            cmd_set(name, value, cred_type)

        elif command == "get":
            if len(sys.argv) < 3:
                print("Error: get command requires NAME")
                sys.exit(1)
            cmd_get(sys.argv[2])

        elif command == "list":
            cred_type = sys.argv[2] if len(sys.argv) > 2 else None
            cmd_list(cred_type)

        elif command == "rotate":
            if len(sys.argv) < 4:
                print("Error: rotate command requires NAME and NEW_VALUE")
                sys.exit(1)
            cmd_rotate(sys.argv[2], sys.argv[3])

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Error: delete command requires NAME")
                sys.exit(1)
            cmd_delete(sys.argv[2])

        elif command == "check-rotation":
            cmd_check_rotation()

        elif command == "health":
            cmd_health()

        elif command == "export":
            cmd_export()

        elif command in ("help", "-h", "--help"):
            print_help()

        else:
            print(f"Error: Unknown command '{command}'")
            print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
