"""
Health check endpoints for the TORE Matrix V3 API.

Provides system health monitoring and status endpoints.
"""

from fastapi import APIRouter
from typing import Dict, Any
import time
from datetime import datetime

router = APIRouter()

@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "TORE Matrix V3 Document Ingestion",
        "version": "3.0.0"
    }

@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check endpoint for Kubernetes.
    
    Returns:
        Service readiness status
    """
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "api": "ready",
            "storage": "ready"
        }
    }

@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint for Kubernetes.
    
    Returns:
        Service liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time()
    }

@router.get("/status")
async def detailed_status() -> Dict[str, Any]:
    """
    Detailed system status endpoint.
    
    Returns:
        Comprehensive system status information
    """
    return {
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "service": {
            "name": "TORE Matrix V3 Document Ingestion",
            "version": "3.0.0",
            "environment": "development"
        },
        "components": {
            "api_server": {
                "status": "healthy",
                "uptime": time.time()
            },
            "document_processor": {
                "status": "ready",
                "queue_size": 0
            },
            "storage": {
                "status": "available",
                "type": "local"
            }
        },
        "metrics": {
            "requests_total": 0,
            "errors_total": 0,
            "average_response_time": 0
        }
    }