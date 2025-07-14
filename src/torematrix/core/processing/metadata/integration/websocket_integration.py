"""WebSocket integration for real-time metadata extraction progress."""

from typing import Dict, List, Set, Any, Optional
import asyncio
import json
import logging
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from torematrix.core.events.event_bus import EventBus
from torematrix.core.events.event_types import ProcessingEvent


class ProgressUpdate(BaseModel):
    """Progress update message model."""
    session_id: str
    document_id: str
    stage: str
    progress_percentage: float
    message: str
    timestamp: datetime
    details: Dict[str, Any]


class ConnectionInfo(BaseModel):
    """WebSocket connection information."""
    connection_id: str
    user_id: str
    session_ids: Set[str]
    connected_at: datetime


class MetadataWebSocketManager:
    """WebSocket manager for real-time metadata extraction progress."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, ConnectionInfo] = {}
        self.session_subscribers: Dict[str, Set[str]] = {}  # session_id -> connection_ids
        self.event_bus = EventBus()
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Initialize WebSocket manager and event subscriptions."""
        await self.event_bus.initialize()
        
        # Subscribe to metadata extraction events
        await self.event_bus.subscribe(
            "metadata.extraction.started",
            self._handle_extraction_started
        )
        await self.event_bus.subscribe(
            "metadata.extraction.progress",
            self._handle_extraction_progress
        )
        await self.event_bus.subscribe(
            "metadata.extraction.completed",
            self._handle_extraction_completed
        )
        await self.event_bus.subscribe(
            "metadata.extraction.failed",
            self._handle_extraction_failed
        )
        
        self.logger.info("WebSocket manager initialized")
        
    async def connect(
        self, 
        websocket: WebSocket, 
        connection_id: str, 
        user_id: str
    ):
        """Accept new WebSocket connection."""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        self.connection_info[connection_id] = ConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            session_ids=set(),
            connected_at=datetime.utcnow()
        )
        
        self.logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
        
        # Send welcome message
        await self._send_to_connection(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to metadata extraction progress stream"
        })
        
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection."""
        if connection_id in self.active_connections:
            # Unsubscribe from all sessions
            if connection_id in self.connection_info:
                connection = self.connection_info[connection_id]
                for session_id in connection.session_ids:
                    await self._unsubscribe_from_session(connection_id, session_id)
                    
            # Remove connection
            del self.active_connections[connection_id]
            del self.connection_info[connection_id]
            
            self.logger.info(f"WebSocket disconnected: {connection_id}")
            
    async def subscribe_to_session(
        self, 
        connection_id: str, 
        session_id: str
    ):
        """Subscribe connection to session progress updates."""
        if connection_id not in self.connection_info:
            raise ValueError(f"Connection not found: {connection_id}")
            
        # Add to session subscribers
        if session_id not in self.session_subscribers:
            self.session_subscribers[session_id] = set()
        self.session_subscribers[session_id].add(connection_id)
        
        # Update connection info
        self.connection_info[connection_id].session_ids.add(session_id)
        
        await self._send_to_connection(connection_id, {
            "type": "subscription_confirmed",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Subscribed to session {session_id}"
        })
        
        self.logger.info(f"Connection {connection_id} subscribed to session {session_id}")
        
    async def _unsubscribe_from_session(
        self, 
        connection_id: str, 
        session_id: str
    ):
        """Unsubscribe connection from session updates."""
        if session_id in self.session_subscribers:
            self.session_subscribers[session_id].discard(connection_id)
            if not self.session_subscribers[session_id]:
                del self.session_subscribers[session_id]
                
        if connection_id in self.connection_info:
            self.connection_info[connection_id].session_ids.discard(session_id)
            
    async def broadcast_progress(
        self, 
        session_id: str, 
        progress_update: ProgressUpdate
    ):
        """Broadcast progress update to all subscribers of a session."""
        if session_id not in self.session_subscribers:
            return
            
        message = {
            "type": "progress_update",
            "session_id": session_id,
            "document_id": progress_update.document_id,
            "stage": progress_update.stage,
            "progress_percentage": progress_update.progress_percentage,
            "message": progress_update.message,
            "timestamp": progress_update.timestamp.isoformat(),
            "details": progress_update.details
        }
        
        # Send to all subscribers
        subscribers = list(self.session_subscribers[session_id])
        await asyncio.gather(*[
            self._send_to_connection(connection_id, message)
            for connection_id in subscribers
        ], return_exceptions=True)
        
    async def _send_to_connection(
        self, 
        connection_id: str, 
        message: Dict[str, Any]
    ):
        """Send message to specific connection."""
        if connection_id not in self.active_connections:
            return
            
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Failed to send message to {connection_id}: {e}")
            await self.disconnect(connection_id)
            
    async def _handle_extraction_started(self, event: ProcessingEvent):
        """Handle metadata extraction started event."""
        session_id = event.data.get("session_id")
        if not session_id:
            return
            
        progress_update = ProgressUpdate(
            session_id=session_id,
            document_id=event.document_id,
            stage="initialization",
            progress_percentage=0.0,
            message="Metadata extraction started",
            timestamp=datetime.utcnow(),
            details={"event_type": "started"}
        )
        
        await self.broadcast_progress(session_id, progress_update)
        
    async def _handle_extraction_progress(self, event: ProcessingEvent):
        """Handle metadata extraction progress event."""
        session_id = event.data.get("session_id")
        if not session_id:
            return
            
        progress_data = event.data.get("progress", {})
        
        progress_update = ProgressUpdate(
            session_id=session_id,
            document_id=event.document_id,
            stage=progress_data.get("stage", "processing"),
            progress_percentage=progress_data.get("percentage", 50.0),
            message=progress_data.get("message", "Processing..."),
            timestamp=datetime.utcnow(),
            details=progress_data
        )
        
        await self.broadcast_progress(session_id, progress_update)
        
    async def _handle_extraction_completed(self, event: ProcessingEvent):
        """Handle metadata extraction completed event."""
        session_id = event.data.get("session_id")
        if not session_id:
            return
            
        stats = event.data.get("stats", {})
        
        progress_update = ProgressUpdate(
            session_id=session_id,
            document_id=event.document_id,
            stage="completed",
            progress_percentage=100.0,
            message="Metadata extraction completed successfully",
            timestamp=datetime.utcnow(),
            details={
                "stats": stats,
                "event_type": "completed"
            }
        )
        
        await self.broadcast_progress(session_id, progress_update)
        
    async def _handle_extraction_failed(self, event: ProcessingEvent):
        """Handle metadata extraction failed event."""
        session_id = event.data.get("session_id")
        if not session_id:
            return
            
        error = event.data.get("error", "Unknown error")
        
        progress_update = ProgressUpdate(
            session_id=session_id,
            document_id=event.document_id,
            stage="failed",
            progress_percentage=0.0,
            message=f"Metadata extraction failed: {error}",
            timestamp=datetime.utcnow(),
            details={
                "error": error,
                "event_type": "failed"
            }
        )
        
        await self.broadcast_progress(session_id, progress_update)
        
    async def handle_websocket_messages(
        self, 
        websocket: WebSocket, 
        connection_id: str
    ):
        """Handle incoming WebSocket messages."""
        try:
            while True:
                # Receive message
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                message_type = message.get("type")
                
                if message_type == "subscribe":
                    session_id = message.get("session_id")
                    if session_id:
                        await self.subscribe_to_session(connection_id, session_id)
                        
                elif message_type == "unsubscribe":
                    session_id = message.get("session_id")
                    if session_id:
                        await self._unsubscribe_from_session(connection_id, session_id)
                        
                elif message_type == "ping":
                    await self._send_to_connection(connection_id, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                else:
                    await self._send_to_connection(connection_id, {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
        except Exception as e:
            self.logger.error(f"WebSocket error for {connection_id}: {e}")
            await self.disconnect(connection_id)
            
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "active_sessions": len(self.session_subscribers),
            "connections_by_user": self._get_connections_by_user(),
            "session_subscriber_counts": {
                session_id: len(subscribers)
                for session_id, subscribers in self.session_subscribers.items()
            }
        }
        
    def _get_connections_by_user(self) -> Dict[str, int]:
        """Get connection count by user."""
        user_counts = {}
        for connection in self.connection_info.values():
            user_id = connection.user_id
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        return user_counts
        
    async def cleanup(self):
        """Cleanup WebSocket manager resources."""
        # Disconnect all connections
        for connection_id in list(self.active_connections.keys()):
            await self.disconnect(connection_id)
            
        await self.event_bus.shutdown()
        self.logger.info("WebSocket manager cleaned up")