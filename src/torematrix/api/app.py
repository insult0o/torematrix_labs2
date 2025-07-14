"""
FastAPI Application for TORE Matrix Labs V3

Main application setup with all routers, middleware, and WebSocket endpoints.
"""

from fastapi import FastAPI, WebSocket, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

# Import routers and WebSocket handlers
from .routers.ingestion import router as ingestion_router
from .websockets.progress import websocket_endpoint, websocket_health
from .models import ErrorResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting TORE Matrix Labs V3 API")
    
    # TODO: Initialize dependencies here
    # - Setup upload manager
    # - Setup queue manager
    # - Setup event bus
    # - Setup progress tracker
    # - Setup database connections
    
    yield
    
    # Shutdown
    logger.info("Shutting down TORE Matrix Labs V3 API")
    
    # TODO: Cleanup resources
    # - Close database connections
    # - Stop background workers
    # - Clean up temporary files


# Create FastAPI application
app = FastAPI(
    title="TORE Matrix Labs V3 API",
    description="Document ingestion and processing API for TORE Matrix Labs V3",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "service": "TORE Matrix Labs V3 API",
        "version": "3.0.0"
    }


# Include API routers
app.include_router(ingestion_router)


# WebSocket endpoints
@app.websocket("/ws/progress/{session_id}")
async def websocket_progress_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
    event_bus = Depends(lambda: None),  # Will be injected
    progress_tracker = Depends(lambda: None)  # Will be injected
):
    """WebSocket endpoint for real-time progress updates."""
    await websocket_endpoint(websocket, session_id, token, event_bus, progress_tracker)


@app.get("/ws/health")
async def websocket_health_endpoint():
    """WebSocket service health check."""
    return await websocket_health()


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            message="An internal server error occurred"
        ).dict()
    )


# Additional middleware for request logging
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all HTTP requests."""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"{response.status_code} - {process_time:.3f}s"
    )
    
    return response


if __name__ == "__main__":
    import uvicorn
    import time
    
    uvicorn.run(
        "torematrix.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )