"""
WebSocket Progress Handler

Manages WebSocket connections for real-time progress updates during
document processing. Integrates with Agent 2's event bus and progress tracker.
"""

from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, Set, Optional, Any
import asyncio
import json
import logging
from datetime import datetime
from collections import defaultdict

# Import dependencies from other agents
from ...core.auth import verify_websocket_token  # Will be implemented
from ...core.events import EventBus, ProcessingEvent  # From Agent 2
from ...ingestion.progress import ProgressTracker, SessionProgress  # From Agent 2

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts.
    
    Handles connection lifecycle, user authentication, and message broadcasting
    to appropriate clients based on session membership.
    """
    
    def __init__(self):
        # Maps session_id to set of websocket connections
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        # Maps connection to user info for tracking
        self._user_info: Dict[WebSocket, Dict[str, Any]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str
    ):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        async with self._lock:
            self._connections[session_id].add(websocket)
            self._user_info[websocket] = {
                "user_id": user_id,
                "session_id": session_id,
                "connected_at": datetime.utcnow()
            }
        
        logger.info(f"WebSocket connected: user={user_id}, session={session_id}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection and cleanup."""
        async with self._lock:
            user_info = self._user_info.pop(websocket, {})
            session_id = user_info.get("session_id")
            
            if session_id and session_id in self._connections:
                self._connections[session_id].discard(websocket)
                
                # Clean up empty session
                if not self._connections[session_id]:
                    del self._connections[session_id]
        
        logger.info(f"WebSocket disconnected: {user_info}")
    
    async def broadcast_to_session(
        self,
        session_id: str,
        message: Dict[str, Any]
    ):
        """Broadcast a message to all connections for a session."""
        async with self._lock:
            connections = self._connections.get(session_id, set()).copy()
        
        if not connections:
            return
        
        # Send to all connections, tracking failures
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def send_to_user(
        self,
        user_id: str,
        message: Dict[str, Any]
    ):
        """Send message to all connections for a specific user."""
        async with self._lock:
            user_connections = [
                ws for ws, info in self._user_info.items()
                if info["user_id"] == user_id
            ]
        
        for websocket in user_connections:
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(websocket)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about current connections."""
        return {
            "total_connections": sum(len(conns) for conns in self._connections.values()),
            "active_sessions": len(self._connections),
            "sessions": {
                session_id: len(conns) 
                for session_id, conns in self._connections.items()
            }
        }


# Global connection manager instance
manager = ConnectionManager()


class ProgressWebSocket:
    """
    Handles progress updates via WebSocket.
    
    Subscribes to processing events from Agent 2 and broadcasts
    them to appropriate WebSocket clients.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        progress_tracker: ProgressTracker
    ):
        self.event_bus = event_bus
        self.progress_tracker = progress_tracker
        self._subscribed = False
    
    async def start(self):
        """Start listening for events from the event bus."""
        if not self._subscribed:
            # Subscribe to all relevant events from Agent 2
            self.event_bus.subscribe(
                "progress_updated",
                self._handle_progress_event
            )
            self.event_bus.subscribe(
                "job_enqueued",
                self._handle_job_event
            )
            self.event_bus.subscribe(
                "document_processed",
                self._handle_completion_event
            )
            self.event_bus.subscribe(
                "document_failed",
                self._handle_failure_event
            )
            self.event_bus.subscribe(
                "batch_completed",
                self._handle_batch_event
            )
            self._subscribed = True
            logger.info("WebSocket event subscriptions started")
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str
    ):
        """
        Handle a WebSocket connection for progress updates.
        
        Manages the connection lifecycle, sends initial state,
        and handles client messages.
        """
        await manager.connect(websocket, session_id, user_id)
        
        try:
            # Send initial progress state
            progress = await self.progress_tracker.get_session_progress(session_id)
            if progress:
                await websocket.send_json({
                    "type": "initial_progress",
                    "data": self._serialize_progress(progress),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Send connection acknowledgment
            await websocket.send_json({
                "type": "connected",
                "data": {
                    "session_id": session_id,
                    "user_id": user_id
                },
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Keep connection alive and handle client messages
            while True:
                # Wait for client messages
                data = await websocket.receive_text()
                
                # Handle different message types
                if data == "ping":
                    await websocket.send_text("pong")
                elif data.startswith("get_file:"):
                    # Client requesting specific file progress
                    file_id = data.split(":", 1)[1]
                    await self._send_file_progress(websocket, session_id, file_id)
                elif data.startswith("get_session:"):
                    # Client requesting session progress refresh
                    await self._send_session_progress(websocket, session_id)
                else:
                    # Log unknown message types
                    logger.warning(f"Unknown WebSocket message: {data}")
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected normally: session={session_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await manager.disconnect(websocket)
    
    async def _handle_progress_event(self, event: ProcessingEvent):
        """Handle progress update events from Agent 2."""
        try:
            # Get session ID for the file
            file_metadata = await self._get_file_session(event.file_id)
            if not file_metadata:
                return
            
            session_id = file_metadata["session_id"]
            
            # Get updated session progress
            progress = await self.progress_tracker.get_session_progress(session_id)
            
            # Broadcast update to session
            await manager.broadcast_to_session(session_id, {
                "type": "progress_update",
                "file_id": event.file_id,
                "data": event.data,
                "session_progress": self._serialize_progress(progress) if progress else None,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling progress event: {e}")
    
    async def _handle_job_event(self, event: ProcessingEvent):
        """Handle job enqueued events."""
        try:
            file_metadata = await self._get_file_session(event.file_id)
            if not file_metadata:
                return
            
            await manager.broadcast_to_session(file_metadata["session_id"], {
                "type": "job_enqueued",
                "file_id": event.file_id,
                "job_id": getattr(event, 'job_id', None),
                "data": event.data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling job event: {e}")
    
    async def _handle_completion_event(self, event: ProcessingEvent):
        """Handle document processed events."""
        try:
            file_metadata = await self._get_file_session(event.file_id)
            if not file_metadata:
                return
            
            session_id = file_metadata["session_id"]
            
            # Update progress tracker
            await self.progress_tracker.update_file_progress(
                event.file_id,
                status="completed",
                current_step="done",
                completed_steps=5  # Assuming 5 total steps
            )
            
            # Get updated session progress
            progress = await self.progress_tracker.get_session_progress(session_id)
            
            await manager.broadcast_to_session(session_id, {
                "type": "document_completed",
                "file_id": event.file_id,
                "data": event.data,
                "session_progress": self._serialize_progress(progress) if progress else None,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling completion event: {e}")
    
    async def _handle_failure_event(self, event: ProcessingEvent):
        """Handle document failed events."""
        try:
            file_metadata = await self._get_file_session(event.file_id)
            if not file_metadata:
                return
            
            session_id = file_metadata["session_id"]
            
            # Update progress tracker
            await self.progress_tracker.update_file_progress(
                event.file_id,
                status="failed",
                current_step="error",
                completed_steps=0,
                error=getattr(event, 'error', 'Processing failed')
            )
            
            # Get updated session progress
            progress = await self.progress_tracker.get_session_progress(session_id)
            
            await manager.broadcast_to_session(session_id, {
                "type": "document_failed",
                "file_id": event.file_id,
                "error": getattr(event, 'error', 'Unknown error'),
                "session_progress": self._serialize_progress(progress) if progress else None,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling failure event: {e}")
    
    async def _handle_batch_event(self, event: ProcessingEvent):
        """Handle batch completion events."""
        try:
            # Batch events may not have a specific file_id
            batch_id = getattr(event, 'batch_id', None)
            if not batch_id:
                return
            
            # For now, broadcast to all active sessions
            # In a real implementation, you'd track which sessions belong to the batch
            for session_id in manager._connections.keys():
                await manager.broadcast_to_session(session_id, {
                    "type": "batch_completed",
                    "batch_id": batch_id,
                    "data": event.data,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error handling batch event: {e}")
    
    async def _send_file_progress(
        self,
        websocket: WebSocket,
        session_id: str,
        file_id: str
    ):
        """Send specific file progress to a client."""
        try:
            progress = await self.progress_tracker.get_session_progress(session_id)
            if progress and file_id in progress.files:
                file_progress = progress.files[file_id]
                await websocket.send_json({
                    "type": "file_progress",
                    "file_id": file_id,
                    "data": {
                        "status": file_progress.status,
                        "progress": file_progress.progress,
                        "current_step": file_progress.current_step,
                        "completed_steps": file_progress.completed_steps,
                        "total_steps": file_progress.total_steps,
                        "error": file_progress.error
                    },
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"File {file_id} not found in session",
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.error(f"Error sending file progress: {e}")
    
    async def _send_session_progress(
        self,
        websocket: WebSocket,
        session_id: str
    ):
        """Send current session progress to a client."""
        try:
            progress = await self.progress_tracker.get_session_progress(session_id)
            if progress:
                await websocket.send_json({
                    "type": "session_progress",
                    "data": self._serialize_progress(progress),
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Session {session_id} not found",
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.error(f"Error sending session progress: {e}")
    
    async def _get_file_session(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session ID for a file.
        
        This is a placeholder - the actual implementation would query
        the database or Agent 1's session manager.
        """
        # TODO: Implement actual session lookup
        # For now, return a placeholder
        return {"session_id": "session-123"}
    
    def _serialize_progress(self, progress: SessionProgress) -> Dict[str, Any]:
        """Serialize progress for JSON transmission."""
        return {
            "session_id": progress.session_id,
            "total_files": progress.total_files,
            "processed_files": progress.processed_files,
            "failed_files": progress.failed_files,
            "overall_progress": progress.overall_progress,
            "files": {
                file_id: {
                    "filename": fp.filename,
                    "status": fp.status,
                    "progress": fp.progress,
                    "current_step": fp.current_step,
                    "completed_steps": fp.completed_steps,
                    "total_steps": fp.total_steps,
                    "error": fp.error,
                    "started_at": fp.started_at.isoformat() if fp.started_at else None,
                    "completed_at": fp.completed_at.isoformat() if fp.completed_at else None
                }
                for file_id, fp in progress.files.items()
            }
        }


# WebSocket endpoint factory
def create_websocket_handler(
    event_bus: EventBus,
    progress_tracker: ProgressTracker
) -> ProgressWebSocket:
    """Factory function to create WebSocket handler with dependencies."""
    return ProgressWebSocket(event_bus, progress_tracker)


# WebSocket endpoint
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
    event_bus: EventBus = Depends(lambda: None),  # Will be provided by dependency injection
    progress_tracker: ProgressTracker = Depends(lambda: None)  # Will be provided by dependency injection
):
    """
    WebSocket endpoint for progress updates.
    
    Clients connect to /ws/progress/{session_id}?token={auth_token}
    to receive real-time updates about file processing progress.
    """
    # Verify authentication token
    user = await verify_websocket_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    # Create and start handler
    handler = ProgressWebSocket(event_bus, progress_tracker)
    await handler.start()
    
    # Handle the connection
    await handler.handle_connection(websocket, session_id, user.id)


# Health check endpoint for WebSocket service
async def websocket_health():
    """Get WebSocket service health and statistics."""
    return {
        "status": "healthy",
        "connections": manager.get_connection_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }

# FastAPI router for WebSocket endpoints
from fastapi import APIRouter

router = APIRouter()

@router.websocket("/progress")
async def websocket_progress_endpoint(websocket: WebSocket, session_id: str = Query(...)):
    """WebSocket endpoint for real-time progress updates."""
    await progress_websocket_endpoint(websocket, session_id)

@router.get("/health")
async def websocket_health_endpoint():
    """WebSocket service health check."""
    return await websocket_health()