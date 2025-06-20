#!/usr/bin/env python3
"""
Project Ekko - FastAPI Backend (Placeholder v1.1)
Corrected lint issues (S104, F821).
"""

import logging
import sys  # Added missing import for sys.exit

from fastapi import FastAPI

logger = logging.getLogger(__name__)
app = FastAPI(title="Project Ekko API", version="0.1.0")


@app.on_event("startup")
async def startup_event():
    """Runs when the API server starts."""
    logger.info("Ekko API starting up...")
    # Add any async setup needed here (e.g., DB connection pool)


@app.on_event("shutdown")
async def shutdown_event():
    """Runs when the API server shuts down."""
    logger.info("Ekko API shutting down...")
    # Add cleanup here


@app.get("/")
async def read_root():
    """Root endpoint."""
    logger.debug("Root endpoint accessed.")
    return {"message": "Welcome to Ekko API v0.1"}


@app.get("/health")
async def health_check():
    """Basic health check."""
    logger.debug("Health check accessed.")
    # TODO: Add checks for DB, LLM connectivity etc.
    return {"status": "ok"}


if __name__ == "__main__":
    try:
        import uvicorn

        logger.info("Running Uvicorn server for development...")
        uvicorn.run(
            "main:app",  # Use string format for reload to work
            host="0.0.0.0",  # nosec B104 - Allow binding to all interfaces for dev/Docker
            port=8888,
            log_level="info",
            reload=True,  # Enable auto-reload for development
        )
    except ImportError:
        logger.error("Uvicorn not installed. Run 'pip install uvicorn[standard]'")
        print("ERROR: Uvicorn not installed.", file=sys.stderr)
        sys.exit("Dependency Error: uvicorn missing")
    except ValueError as e:
        logger.error(f"Value error occurred: {e}")
        # Handle specific ValueError exceptions
    except KeyError as e:
        logger.error(f"Key error occurred: {e}")
        # Handle specific KeyError exceptions
    except OSError as e:
        logger.critical(f"OS error occurred: {e}")
        # Handle specific OS-related exceptions
    except Exception as e:
        logger.critical(f"Failed to start Uvicorn: {e}", exc_info=True)
        # Catch-all for unexpected exceptions
        sys.exit(f"API Startup Error: {e}")
