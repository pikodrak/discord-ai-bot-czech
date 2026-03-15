#!/usr/bin/env python3
"""
Bot Restart API Integration Examples

This file demonstrates how to integrate with the bot restart mechanism
from various client applications.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional

import httpx


class BotControlClient:
    """
    Client for interacting with the bot control API.

    Provides convenient methods for starting, stopping, restarting,
    and monitoring the Discord bot.
    """

    def __init__(self, base_url: str = "http://localhost:8080", api_token: Optional[str] = None):
        """
        Initialize the bot control client.

        Args:
            base_url: Base URL of the API server
            api_token: Optional JWT token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.client = httpx.AsyncClient(base_url=base_url)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def get_status(self) -> Dict[str, Any]:
        """
        Get current bot status.

        Returns:
            Dict with bot status information

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        response = await self.client.get(
            "/api/bot/status",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def restart_bot(
        self,
        timeout: float = 10.0,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Restart the bot process.

        Args:
            timeout: Maximum seconds to wait for shutdown
            env_vars: Optional environment variables to pass

        Returns:
            Dict with restart result

        Raises:
            httpx.HTTPStatusError: If restart fails
        """
        payload = {"timeout": timeout}
        if env_vars:
            payload["env_vars"] = env_vars

        response = await self.client.post(
            "/api/bot/restart",
            json=payload,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def start_bot(self, env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Start the bot process.

        Args:
            env_vars: Optional environment variables to pass

        Returns:
            Dict with start result

        Raises:
            httpx.HTTPStatusError: If start fails
        """
        payload = {"action": "start"}
        if env_vars:
            payload["env_vars"] = env_vars

        response = await self.client.post(
            "/api/bot/control",
            json=payload,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def stop_bot(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Stop the bot process.

        Args:
            timeout: Maximum seconds to wait for shutdown

        Returns:
            Dict with stop result

        Raises:
            httpx.HTTPStatusError: If stop fails
        """
        payload = {
            "action": "stop",
            "timeout": timeout
        }

        response = await self.client.post(
            "/api/bot/control",
            json=payload,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get bot statistics.

        Returns:
            Dict with bot statistics

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        response = await self.client.get(
            "/api/bot/stats",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def check_health(self) -> Dict[str, Any]:
        """
        Check bot health.

        Returns:
            Dict with health status

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        response = await self.client.get(
            "/api/bot/health",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def wait_for_state(
        self,
        target_state: str,
        timeout: float = 30.0,
        poll_interval: float = 1.0
    ) -> bool:
        """
        Wait for bot to reach a specific state.

        Args:
            target_state: State to wait for (e.g., "running", "stopped")
            timeout: Maximum time to wait in seconds
            poll_interval: Interval between status checks in seconds

        Returns:
            True if state reached, False if timeout

        Raises:
            httpx.HTTPStatusError: If status check fails
        """
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            status = await self.get_status()
            if status["state"] == target_state:
                return True

            await asyncio.sleep(poll_interval)

        return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


# Example 1: Simple restart
async def example_simple_restart():
    """Example: Simple bot restart."""
    print("Example 1: Simple bot restart")
    print("-" * 50)

    client = BotControlClient()

    try:
        # Check current status
        status = await client.get_status()
        print(f"Current state: {status['state']}")
        print(f"PID: {status.get('pid', 'N/A')}")

        # Restart the bot
        print("\nRestarting bot...")
        result = await client.restart_bot()

        print(f"✓ Restart successful!")
        print(f"  Previous state: {result['previous_state']}")
        print(f"  Current state: {result['current_state']}")
        print(f"  New PID: {result['pid']}")
        print(f"  Restart count: {result['restart_count']}")

    except httpx.HTTPStatusError as e:
        print(f"✗ Restart failed: {e.response.status_code}")
        print(f"  Error: {e.response.text}")

    finally:
        await client.close()


# Example 2: Restart with custom timeout
async def example_restart_with_timeout():
    """Example: Restart with custom timeout."""
    print("\nExample 2: Restart with custom timeout")
    print("-" * 50)

    client = BotControlClient()

    try:
        # Restart with 20 second timeout
        result = await client.restart_bot(timeout=20.0)

        print(f"✓ Bot restarted with 20s timeout")
        print(f"  New PID: {result['pid']}")

    except httpx.HTTPStatusError as e:
        print(f"✗ Restart failed: {e}")

    finally:
        await client.close()


# Example 3: Restart with environment variables
async def example_restart_with_env():
    """Example: Restart with environment variables."""
    print("\nExample 3: Restart with environment variables")
    print("-" * 50)

    client = BotControlClient()

    try:
        # Restart with custom environment variables
        env_vars = {
            "LOG_LEVEL": "DEBUG",
            "ENVIRONMENT": "staging"
        }

        result = await client.restart_bot(env_vars=env_vars)

        print(f"✓ Bot restarted with custom environment")
        print(f"  Environment: {env_vars}")
        print(f"  New PID: {result['pid']}")

    except httpx.HTTPStatusError as e:
        print(f"✗ Restart failed: {e}")

    finally:
        await client.close()


# Example 4: Configuration update workflow
async def example_config_update_workflow():
    """Example: Complete configuration update workflow."""
    print("\nExample 4: Configuration update workflow")
    print("-" * 50)

    client = BotControlClient()

    try:
        # Step 1: Get current config
        print("1. Getting current configuration...")
        async with httpx.AsyncClient() as http_client:
            config_response = await http_client.get("http://localhost:8080/api/config/current")
            current_config = config_response.json()
            print(f"   Current AI provider: {current_config.get('ai_provider', 'N/A')}")

        # Step 2: Update configuration
        print("\n2. Updating configuration...")
        new_config = {
            "ai_provider": "anthropic",
            "log_level": "INFO"
        }

        async with httpx.AsyncClient() as http_client:
            update_response = await http_client.post(
                "http://localhost:8080/api/config/update",
                json=new_config
            )
            print(f"   ✓ Configuration updated")

        # Step 3: Restart bot to apply changes
        print("\n3. Restarting bot to apply changes...")
        result = await client.restart_bot()
        print(f"   ✓ Bot restarted (PID: {result['pid']})")

        # Step 4: Verify bot is running
        print("\n4. Verifying bot status...")
        await asyncio.sleep(2)  # Give bot time to start
        status = await client.get_status()

        if status['running']:
            print(f"   ✓ Bot is running")
            print(f"   State: {status['state']}")
            print(f"   Uptime: {status.get('uptime_seconds', 0):.1f}s")
        else:
            print(f"   ✗ Bot is not running")

    except Exception as e:
        print(f"✗ Workflow failed: {e}")

    finally:
        await client.close()


# Example 5: Monitor bot status
async def example_monitor_status():
    """Example: Monitor bot status and resource usage."""
    print("\nExample 5: Monitor bot status")
    print("-" * 50)

    client = BotControlClient()

    try:
        status = await client.get_status()

        print(f"Bot Status:")
        print(f"  State: {status['state']}")
        print(f"  Running: {status['running']}")
        print(f"  PID: {status.get('pid', 'N/A')}")

        if status['running']:
            print(f"\nResource Usage:")
            print(f"  Uptime: {status.get('uptime_seconds', 0):.1f}s")
            print(f"  CPU: {status.get('cpu_percent', 0):.1f}%")
            print(f"  Memory: {status.get('memory_mb', 0):.2f} MB")
            print(f"  Restart count: {status.get('restart_count', 0)}")

        # Get statistics
        stats = await client.get_stats()
        print(f"\nStatistics:")
        print(f"  Uptime: {stats.get('uptime_hours', 0):.2f} hours")
        print(f"  Messages processed: {stats.get('total_messages_processed', 0)}")
        print(f"  Responses sent: {stats.get('total_responses_sent', 0)}")

    except Exception as e:
        print(f"✗ Failed to get status: {e}")

    finally:
        await client.close()


# Example 6: Graceful stop and start
async def example_stop_and_start():
    """Example: Gracefully stop and start bot."""
    print("\nExample 6: Graceful stop and start")
    print("-" * 50)

    client = BotControlClient()

    try:
        # Stop the bot
        print("1. Stopping bot...")
        stop_result = await client.stop_bot(timeout=15.0)
        print(f"   ✓ {stop_result['message']}")

        # Wait for stop to complete
        print("\n2. Waiting for bot to stop...")
        stopped = await client.wait_for_state("stopped", timeout=20.0)

        if stopped:
            print("   ✓ Bot stopped")
        else:
            print("   ✗ Bot did not stop in time")
            return

        # Wait a moment
        await asyncio.sleep(2)

        # Start the bot
        print("\n3. Starting bot...")
        start_result = await client.start_bot()
        print(f"   ✓ {start_result['message']}")

        # Wait for start to complete
        print("\n4. Waiting for bot to start...")
        running = await client.wait_for_state("running", timeout=30.0)

        if running:
            status = await client.get_status()
            print(f"   ✓ Bot started (PID: {status['pid']})")
        else:
            print("   ✗ Bot did not start in time")

    except Exception as e:
        print(f"✗ Operation failed: {e}")

    finally:
        await client.close()


# Main function to run all examples
async def main():
    """Run all examples."""
    print("=" * 70)
    print("Bot Restart API Integration Examples")
    print("=" * 70)

    # Run examples
    # Note: Comment out examples you don't want to run
    await example_simple_restart()
    # await example_restart_with_timeout()
    # await example_restart_with_env()
    # await example_config_update_workflow()
    await example_monitor_status()
    # await example_stop_and_start()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nExamples failed: {e}")
        import traceback
        traceback.print_exc()
