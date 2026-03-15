#!/usr/bin/env python3
"""
FastAPI Server Startup Script

This script starts the FastAPI admin interface server with proper configuration
and error handling. It can be run directly or imported by other modules.
"""

import logging
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main() -> None:
    """
    Main entry point for the FastAPI server.

    Loads environment configuration and starts the uvicorn server
    with settings from the .env file.
    """
    # Load environment variables
    load_dotenv()

    # Import settings after loading .env
    from src.config import get_settings

    try:
        settings = get_settings()
    except Exception as e:
        logging.error(f"Failed to load settings: {e}")
        sys.exit(1)

    # Configure logging
    log_level = settings.log_level.lower()

    # Start the server
    try:
        uvicorn.run(
            "app:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_reload,
            log_level=log_level,
            access_log=True,
        )
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
