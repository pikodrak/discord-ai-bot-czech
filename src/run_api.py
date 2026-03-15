#!/usr/bin/env python3
"""
FastAPI Server Startup Script

This script provides a programmatic way to start the FastAPI admin interface
server. It can be imported and used by other modules that need to launch
the API server programmatically.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def start_api_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
    reload: Optional[bool] = None,
    log_level: Optional[str] = None
) -> None:
    """
    Start the FastAPI server with configuration from environment or parameters.

    Args:
        host: Server host address (default: from settings or 0.0.0.0)
        port: Server port (default: from settings or 8000)
        reload: Enable auto-reload on code changes (default: from settings or False)
        log_level: Logging level (default: from settings or 'info')

    Raises:
        SystemExit: If server fails to start or configuration is invalid
    """
    # Load environment variables
    load_dotenv()

    # Import settings after loading .env to ensure environment variables are available
    try:
        from src.config import get_settings
        settings = get_settings()
    except ImportError:
        logger.warning("Could not import settings from src.config, using defaults")
        # Use defaults if config is not available
        settings = None
    except Exception as e:
        logger.error(f"Failed to load settings: {e}", exc_info=True)
        sys.exit(1)

    # Determine server configuration
    if settings:
        server_host = host or getattr(settings, 'api_host', '0.0.0.0')
        server_port = port or getattr(settings, 'api_port', 8000)
        server_reload = reload if reload is not None else getattr(settings, 'api_reload', False)
        server_log_level = log_level or getattr(settings, 'log_level', 'info').lower()
    else:
        server_host = host or '0.0.0.0'
        server_port = port or 8000
        server_reload = reload if reload is not None else False
        server_log_level = log_level or 'info'

    logger.info(f"Starting FastAPI server on {server_host}:{server_port}")
    logger.info(f"Reload enabled: {server_reload}")
    logger.info(f"Log level: {server_log_level}")

    try:
        # Start uvicorn server
        uvicorn.run(
            "app:app",
            host=server_host,
            port=server_port,
            reload=server_reload,
            log_level=server_log_level,
            access_log=True,
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


def main() -> None:
    """
    Main entry point for command-line execution.

    This function is called when the script is run directly from the command line.
    It starts the server with configuration from environment variables.
    """
    start_api_server()


if __name__ == "__main__":
    main()
