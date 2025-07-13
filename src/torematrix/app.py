#!/usr/bin/env python3
"""
TORE Matrix V3 - Main Application Entry Point

Complete FastAPI application with integrated document ingestion system.
Brings together all Agent 1-4 components for production deployment.
"""

import asyncio
import logging
import uvicorn
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

# from torematrix.core.config import get_settings  # Not needed for basic functionality
from torematrix.core.dependencies import configure_dependencies
from torematrix.ingestion.integration import IngestionSystem, IngestionSettings
from torematrix.api.routers import ingestion, health
from torematrix.api.websockets.progress import router as websocket_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("🚀 Starting TORE Matrix V3 Document Ingestion System")
    
    # Initialize core system
    try:
        settings = IngestionSettings()
        ingestion_system = IngestionSystem(settings)
        
        # Initialize the system
        await ingestion_system.initialize()
        logger.info("✅ Ingestion system initialized")
        
        # Configure dependencies
        configure_dependencies(
            upload_manager=ingestion_system.upload_manager,
            queue_manager=ingestion_system.queue_manager,
            event_bus=ingestion_system.event_bus,
            progress_tracker=ingestion_system.progress_tracker
        )
        logger.info("✅ Dependencies configured")
        
        # Store system in app state
        app.state.ingestion_system = ingestion_system
        
        # Check system status
        status = await ingestion_system.get_integration_status()
        logger.info(f"🔧 System status: {status}")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        raise
    
    finally:
        # Cleanup
        logger.info("🔄 Shutting down TORE Matrix V3")
        if hasattr(app.state, 'ingestion_system'):
            await app.state.ingestion_system.shutdown()
        logger.info("✅ Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Application configuration
    app = FastAPI(
        title="TORE Matrix V3 Document Ingestion API",
        description="Enterprise-grade document processing pipeline with real-time progress tracking",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://app.torematrix.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Include routers
    app.include_router(
        health.router,
        prefix="/health",
        tags=["Health"]
    )
    
    app.include_router(
        ingestion.router,
        prefix="/api/v1/ingestion",
        tags=["Document Ingestion"]
    )
    
    app.include_router(
        websocket_router,
        prefix="/ws",
        tags=["WebSocket"]
    )
    
    # Static files (if needed)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    @app.get("/")
    async def root():
        """Root endpoint with system information."""
        return {
            "service": "TORE Matrix V3 Document Ingestion",
            "version": "3.0.0",
            "status": "operational",
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1"
        }
    
    @app.get("/api/v1")
    async def api_info():
        """API information endpoint."""
        return {
            "api_version": "v1",
            "endpoints": {
                "upload": "/api/v1/ingestion/upload",
                "sessions": "/api/v1/ingestion/sessions",
                "files": "/api/v1/ingestion/files",
                "progress": "/ws/progress"
            },
            "documentation": "/docs"
        }
    
    return app


def run_development_server():
    """Run the development server."""
    logger.info("🔧 Starting development server")
    
    app = create_app()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )


def run_production_server():
    """Run the production server."""
    logger.info("🚀 Starting production server")
    
    app = create_app()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=4,
        log_level="info",
        access_log=True,
        loop="asyncio"
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "production":
        run_production_server()
    else:
        run_development_server()