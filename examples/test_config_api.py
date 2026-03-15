#!/usr/bin/env python3
"""
Test script for Configuration API endpoints.

This script demonstrates how to use the configuration API endpoints
and validates that they work correctly.
"""

import asyncio
import json
from typing import Dict, Any

import httpx


# API Configuration
API_BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"


class ConfigAPIClient:
    """Client for testing Configuration API endpoints."""

    def __init__(self, base_url: str):
        """
        Initialize API client.

        Args:
            base_url: Base URL for the API
        """
        self.base_url = base_url
        self.token: str | None = None
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Login and obtain JWT token.

        Args:
            username: Admin username
            password: Admin password

        Returns:
            Login response with access token
        """
        response = await self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        print(f"✓ Logged in successfully. Token: {self.token[:20]}...")
        return data

    def get_headers(self) -> Dict[str, str]:
        """
        Get request headers with authentication.

        Returns:
            Headers dictionary with Bearer token
        """
        if not self.token:
            raise ValueError("Not authenticated. Call login() first.")
        return {"Authorization": f"Bearer {self.token}"}

    async def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration.

        Returns:
            Configuration response
        """
        response = await self.client.get("/api/config/")
        response.raise_for_status()
        data = response.json()
        print("✓ Retrieved configuration")
        return data

    async def get_secrets(self) -> Dict[str, Any]:
        """
        Get configuration secrets (masked).

        Returns:
            Secrets response
        """
        response = await self.client.get(
            "/api/config/secrets",
            headers=self.get_headers()
        )
        response.raise_for_status()
        data = response.json()
        print("✓ Retrieved masked secrets")
        return data

    async def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update configuration.

        Args:
            updates: Configuration updates

        Returns:
            Update response
        """
        response = await self.client.put(
            "/api/config/",
            headers=self.get_headers(),
            json=updates
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ Updated configuration: {data.get('updated_fields', [])}")
        return data

    async def update_discord(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update Discord configuration.

        Args:
            updates: Discord updates

        Returns:
            Update response
        """
        response = await self.client.patch(
            "/api/config/discord",
            headers=self.get_headers(),
            json=updates
        )
        response.raise_for_status()
        data = response.json()
        print("✓ Updated Discord configuration")
        return data

    async def update_ai(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update AI configuration.

        Args:
            updates: AI updates

        Returns:
            Update response
        """
        response = await self.client.patch(
            "/api/config/ai",
            headers=self.get_headers(),
            json=updates
        )
        response.raise_for_status()
        data = response.json()
        print("✓ Updated AI configuration")
        return data

    async def update_behavior(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update behavior configuration.

        Args:
            updates: Behavior updates

        Returns:
            Update response
        """
        response = await self.client.patch(
            "/api/config/behavior",
            headers=self.get_headers(),
            json=updates
        )
        response.raise_for_status()
        data = response.json()
        print("✓ Updated behavior configuration")
        return data

    async def validate_config(self) -> Dict[str, Any]:
        """
        Validate configuration.

        Returns:
            Validation results
        """
        response = await self.client.get("/api/config/validate")
        response.raise_for_status()
        data = response.json()
        print(f"✓ Validation result: {'Valid' if data['valid'] else 'Invalid'}")
        if data.get("errors"):
            print(f"  Errors: {data['errors']}")
        if data.get("warnings"):
            print(f"  Warnings: {data['warnings']}")
        return data

    async def reload_config(self) -> Dict[str, Any]:
        """
        Reload configuration from disk.

        Returns:
            Reload response
        """
        response = await self.client.post(
            "/api/config/reload",
            headers=self.get_headers()
        )
        response.raise_for_status()
        data = response.json()
        print("✓ Reloaded configuration from disk")
        return data

    async def export_config(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """
        Export configuration.

        Args:
            mask_secrets: Whether to mask secrets

        Returns:
            Configuration export
        """
        response = await self.client.get(
            f"/api/config/export?mask_secrets={str(mask_secrets).lower()}",
            headers=self.get_headers()
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ Exported configuration (mask_secrets={mask_secrets})")
        return data

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


async def run_tests() -> None:
    """Run comprehensive tests of Configuration API endpoints."""
    print("=" * 60)
    print("Configuration API Test Suite")
    print("=" * 60)
    print()

    client = ConfigAPIClient(API_BASE_URL)

    try:
        # Test 1: Get configuration (no auth required)
        print("Test 1: Get Current Configuration")
        print("-" * 60)
        config = await client.get_config()
        print(json.dumps(config, indent=2))
        print()

        # Test 2: Login
        print("Test 2: Admin Login")
        print("-" * 60)
        await client.login(ADMIN_USERNAME, ADMIN_PASSWORD)
        print()

        # Test 3: Get secrets
        print("Test 3: Get Masked Secrets")
        print("-" * 60)
        secrets = await client.get_secrets()
        print(json.dumps(secrets, indent=2))
        print()

        # Test 4: Validate configuration
        print("Test 4: Validate Configuration")
        print("-" * 60)
        validation = await client.validate_config()
        print()

        # Test 5: Update behavior settings
        print("Test 5: Update Behavior Settings")
        print("-" * 60)
        behavior_update = {
            "bot_language": "en",
            "bot_response_threshold": 0.75
        }
        await client.update_behavior(behavior_update)
        print()

        # Test 6: Update Discord settings (if you have test channel IDs)
        print("Test 6: Update Discord Settings")
        print("-" * 60)
        try:
            discord_update = {
                "discord_channel_ids": "123456789,987654321"
            }
            await client.update_discord(discord_update)
        except httpx.HTTPStatusError as e:
            print(f"⚠ Discord update skipped (expected if no token set): {e}")
        print()

        # Test 7: Update via general endpoint
        print("Test 7: Update via General Endpoint")
        print("-" * 60)
        general_update = {
            "bot_max_history": 75,
            "log_level": "INFO"
        }
        await client.update_config(general_update)
        print()

        # Test 8: Export configuration
        print("Test 8: Export Configuration (Masked)")
        print("-" * 60)
        export = await client.export_config(mask_secrets=True)
        print(f"Exported {len(export)} configuration keys")
        print()

        # Test 9: Verify changes
        print("Test 9: Verify Configuration Changes")
        print("-" * 60)
        updated_config = await client.get_config()
        print(f"Bot Language: {updated_config['bot_settings']['language']}")
        print(f"Response Threshold: {updated_config['bot_settings']['response_threshold']}")
        print(f"Max History: {updated_config['bot_settings']['max_history']}")
        print()

        # Test 10: Reload configuration
        print("Test 10: Reload Configuration")
        print("-" * 60)
        await client.reload_config()
        print()

        print("=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


async def test_error_handling() -> None:
    """Test error handling and validation."""
    print("\n" + "=" * 60)
    print("Error Handling Tests")
    print("=" * 60)
    print()

    client = ConfigAPIClient(API_BASE_URL)

    try:
        await client.login(ADMIN_USERNAME, ADMIN_PASSWORD)

        # Test invalid language code
        print("Test: Invalid Language Code")
        print("-" * 60)
        try:
            await client.update_behavior({"bot_language": "invalid"})
            print("❌ Should have raised validation error")
        except httpx.HTTPStatusError as e:
            print(f"✓ Correctly rejected invalid language: {e.response.status_code}")
        print()

        # Test invalid threshold
        print("Test: Invalid Threshold")
        print("-" * 60)
        try:
            await client.update_behavior({"bot_response_threshold": 1.5})
            print("❌ Should have raised validation error")
        except httpx.HTTPStatusError as e:
            print(f"✓ Correctly rejected invalid threshold: {e.response.status_code}")
        print()

        # Test unauthorized access to secrets
        print("Test: Unauthorized Access")
        print("-" * 60)
        client.token = None  # Remove token
        try:
            await client.get_secrets()
            print("❌ Should have raised auth error")
        except httpx.HTTPStatusError as e:
            print(f"✓ Correctly rejected unauthorized request: {e.response.status_code}")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    print("Starting Configuration API Tests...")
    print()
    print("Make sure the API server is running:")
    print("  python run_api.py")
    print()
    input("Press Enter to continue...")
    print()

    # Run main tests
    asyncio.run(run_tests())

    # Run error handling tests
    asyncio.run(test_error_handling())
