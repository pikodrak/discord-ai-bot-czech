"""
FastAPI Admin Interface Application

This module provides the main FastAPI application for managing the Discord AI bot,
including authentication, configuration management, and bot control endpoints.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config import get_settings, Settings
from src.api import auth, bot, config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("fastapi_admin")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events for the FastAPI application,
    including loading configuration and cleaning up resources.

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    # Startup
    logger.info("Starting FastAPI admin interface...")

    # Load environment variables
    load_dotenv()

    # Load and validate settings
    try:
        settings = get_settings()
        logger.info(f"Configuration loaded: {settings}")

        # Create necessary directories
        Path("logs").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)

        logger.info(f"Admin interface starting on {settings.api_host}:{settings.api_port}")

    except Exception as e:
        logger.error(f"Failed to load configuration: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down FastAPI admin interface...")


# Create FastAPI application
app = FastAPI(
    title="Discord AI Bot Admin Interface",
    description="Admin interface for managing Discord AI bot configuration and operations",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    Handle ValueError exceptions.

    Args:
        request: HTTP request
        exc: ValueError exception

    Returns:
        JSON error response
    """
    logger.error(f"ValueError: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle general exceptions.

    Args:
        request: HTTP request
        exc: Exception

    Returns:
        JSON error response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    logger.info(f"Static files mounted from: {static_path}")
else:
    logger.warning(f"Static directory not found: {static_path}")


# Include routers
app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"]
)

app.include_router(
    config.router,
    prefix="/api/config",
    tags=["Configuration"]
)

app.include_router(
    bot.router,
    prefix="/api/bot",
    tags=["Bot Management"]
)


# Root endpoint - serve frontend
@app.get("/", tags=["Root"])
async def root() -> FileResponse:
    """
    Root endpoint - serves the admin panel frontend.

    Returns:
        HTML page with the admin interface
    """
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    else:
        return JSONResponse(
            content={
                "message": "Discord AI Bot Admin Interface",
                "version": "1.0.0",
                "docs": "/docs",
                "health": "/health",
                "note": "Frontend not found. API endpoints are available."
            }
        )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check(settings: Settings = get_settings) -> dict:
    """
    Health check endpoint.

    Args:
        settings: Application settings

    Returns:
        Health status information
    """
    # Simplified health check without Settings methods that don't exist yet
    return {
        "status": "healthy",
        "api_version": "1.0.0"
    }


def create_app() -> FastAPI:
    """
    Application factory function for tests.

    Returns:
        The configured FastAPI application instance
    """
    return app


# Run with uvicorn when executed directly
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level="info"
    )
