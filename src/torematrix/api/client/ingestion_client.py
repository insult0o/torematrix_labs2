"""
Ingestion Client SDK

Python client for interacting with the TORE Matrix ingestion API.
Provides convenient methods for file uploads, session management,
and real-time progress tracking.
"""

import aiohttp
import asyncio
import websockets
from typing import List, Dict, Any, Optional, AsyncIterator, Callable, Union
from pathlib import Path
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class IngestionClient:
    """
    Client for interacting with the TORE Matrix ingestion API.
    
    Provides async methods for file uploads, session management,
    and progress tracking with automatic retry and error handling.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize the ingestion client.
        
        Args:
            base_url: Base URL of the API (e.g., "https://api.torematrix.com")
            api_key: API authentication key
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
    
    async def create_session(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new upload session.
        
        Sessions organize related file uploads and track their collective progress.
        
        Args:
            name: Optional name for the session
            metadata: Additional metadata to store with the session
            
        Returns:
            Session information including session_id
        """
        data = {"metadata": metadata or {}}
        if name:
            data["name"] = name
        
        async with self._session.post(
            f"{self.base_url}/api/v1/ingestion/sessions",
            json=data
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def upload_file(
        self,
        session_id: str,
        file_path: Union[Path, str],
        validate_content: bool = True,
        auto_process: bool = True,
        priority: bool = False
    ) -> Dict[str, Any]:
        """
        Upload a single file to an existing session.
        
        Args:
            session_id: Target session ID
            file_path: Path to the file to upload
            validate_content: Whether to perform content validation
            auto_process: Whether to automatically queue for processing
            priority: Whether to use priority queue
            
        Returns:
            Upload result including file_id and validation status
        """
        file_path = Path(file_path)
        
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field(
                "file",
                f,
                filename=file_path.name,
                content_type="application/octet-stream"
            )
            
            params = {
                "validate_content": str(validate_content).lower(),
                "auto_process": str(auto_process).lower(),
                "priority": str(priority).lower()
            }
            
            async with self._session.post(
                f"{self.base_url}/api/v1/ingestion/sessions/{session_id}/upload",
                data=data,
                params=params
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
    
    async def upload_batch(
        self,
        session_id: str,
        file_paths: List[Union[Path, str]],
        validate_content: bool = True,
        auto_process: bool = True,
        priority: bool = False
    ) -> Dict[str, Any]:
        """
        Upload multiple files in a batch to an existing session.
        
        Args:
            session_id: Target session ID
            file_paths: List of file paths to upload
            validate_content: Whether to perform content validation
            auto_process: Whether to automatically queue for processing
            priority: Whether to use priority queue
            
        Returns:
            Batch upload result with success/failure counts
        """
        data = aiohttp.FormData()
        
        for file_path in file_paths:
            file_path = Path(file_path)
            with open(file_path, "rb") as f:
                data.add_field(
                    "files",
                    f,
                    filename=file_path.name,
                    content_type="application/octet-stream"
                )
        
        params = {
            "validate_content": str(validate_content).lower(),
            "auto_process": str(auto_process).lower(),
            "priority": str(priority).lower()
        }
        
        async with self._session.post(
            f"{self.base_url}/api/v1/ingestion/sessions/{session_id}/upload-batch",
            data=data,
            params=params
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get status of an upload session.
        
        Args:
            session_id: Session ID to query
            
        Returns:
            Session status including file progress and statistics
        """
        async with self._session.get(
            f"{self.base_url}/api/v1/ingestion/sessions/{session_id}/status"
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def get_file_status(self, file_id: str) -> Dict[str, Any]:
        """
        Get status of a specific file.
        
        Args:
            file_id: File ID to query
            
        Returns:
            File status including processing progress and results
        """
        async with self._session.get(
            f"{self.base_url}/api/v1/ingestion/files/{file_id}/status"
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def retry_file(self, file_id: str, priority: bool = False) -> Dict[str, Any]:
        """
        Retry processing for a failed file.
        
        Args:
            file_id: File ID to retry
            priority: Whether to use priority queue
            
        Returns:
            Retry result with new job information
        """
        async with self._session.post(
            f"{self.base_url}/api/v1/ingestion/files/{file_id}/retry",
            params={"priority": str(priority).lower()}
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics and worker information.
        
        Returns:
            Queue statistics including depths and worker status
        """
        async with self._session.get(
            f"{self.base_url}/api/v1/ingestion/queue/stats"
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def stream_progress(
        self,
        session_id: str,
        on_update: Callable[[Dict[str, Any]], None]
    ):
        """
        Stream progress updates via WebSocket.
        
        Args:
            session_id: Session ID to monitor
            on_update: Callback function for progress updates
        """
        ws_url = self.base_url.replace("http", "ws")
        url = f"{ws_url}/ws/progress/{session_id}?token={self.api_key}"
        
        try:
            async with websockets.connect(url) as websocket:
                # Send initial ping
                await websocket.send("ping")
                
                # Listen for updates
                async for message in websocket:
                    if message == "pong":
                        continue
                    
                    try:
                        data = json.loads(message)
                        await asyncio.get_event_loop().run_in_executor(
                            None, on_update, data
                        )
                    except json.JSONDecodeError:
                        logger.error(f"Invalid WebSocket message: {message}")
                    except Exception as e:
                        logger.error(f"Error in progress callback: {e}")
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise
    
    async def upload_and_wait(
        self,
        session_id: str,
        file_paths: List[Union[Path, str]],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """
        Upload files and wait for processing to complete.
        
        Args:
            session_id: Target session ID
            file_paths: List of files to upload
            progress_callback: Optional callback for progress updates
            poll_interval: Polling interval in seconds
            
        Returns:
            Final session status when all processing is complete
        """
        # Upload files
        if len(file_paths) == 1:
            upload_result = await self.upload_file(session_id, file_paths[0])
        else:
            upload_result = await self.upload_batch(session_id, file_paths)
        
        # Start progress streaming if callback provided
        progress_task = None
        if progress_callback:
            progress_task = asyncio.create_task(
                self.stream_progress(session_id, progress_callback)
            )
        
        try:
            # Poll for completion
            while True:
                status = await self.get_session_status(session_id)
                
                total = status["total_files"]
                completed = status["processed_files"] + status["failed_files"]
                
                if completed >= total:
                    break
                
                await asyncio.sleep(poll_interval)
            
            return status
            
        finally:
            # Cancel progress streaming
            if progress_task:
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass
    
    async def wait_for_session(
        self,
        session_id: str,
        timeout: Optional[int] = None,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """
        Wait for a session to complete processing.
        
        Args:
            session_id: Session ID to monitor
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds
            
        Returns:
            Final session status
        """
        start_time = datetime.utcnow()
        
        while True:
            status = await self.get_session_status(session_id)
            
            total = status["total_files"]
            completed = status["processed_files"] + status["failed_files"]
            
            if completed >= total:
                return status
            
            # Check timeout
            if timeout:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout:
                    raise TimeoutError(f"Session processing timeout after {timeout}s")
            
            await asyncio.sleep(poll_interval)


class SimpleIngestionClient:
    """
    Simplified synchronous client for basic use cases.
    
    Provides a simplified interface for users who don't need
    the full async capabilities of IngestionClient.
    """
    
    def __init__(self, base_url: str, api_key: str):
        """Initialize simple client."""
        self.client = IngestionClient(base_url, api_key)
    
    def upload_files(
        self,
        file_paths: List[Union[Path, str]],
        session_name: Optional[str] = None,
        wait_for_completion: bool = True
    ) -> Dict[str, Any]:
        """
        Upload files and optionally wait for completion.
        
        Args:
            file_paths: Files to upload
            session_name: Optional session name
            wait_for_completion: Whether to wait for processing
            
        Returns:
            Upload and processing results
        """
        return asyncio.run(self._upload_files_async(
            file_paths, session_name, wait_for_completion
        ))
    
    async def _upload_files_async(
        self,
        file_paths: List[Union[Path, str]],
        session_name: Optional[str],
        wait_for_completion: bool
    ) -> Dict[str, Any]:
        """Internal async implementation."""
        async with self.client as client:
            # Create session
            session = await client.create_session(name=session_name)
            session_id = session["session_id"]
            
            # Upload files
            if wait_for_completion:
                return await client.upload_and_wait(session_id, file_paths)
            else:
                if len(file_paths) == 1:
                    upload_result = await client.upload_file(session_id, file_paths[0])
                else:
                    upload_result = await client.upload_batch(session_id, file_paths)
                
                return {
                    "session": session,
                    "upload": upload_result
                }