"""
WebSocket Connection Manager — Redis Pub/Sub Edition
=====================================================

Manages per-job WebSocket connections. When a worker (which lives in a
separate process) publishes a job update to Redis, the subscriber loop
running inside this API instance picks it up and fans it out to all
locally-connected WebSocket clients for that job_id.

This means multiple API nodes can each run their own WebSocket
connections, and they will ALL receive updates from the shared Redis
channel.
"""

from typing import Dict, Optional, Set
import asyncio
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Map of job_id → set of active WebSocket connections on THIS node
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._subscriber_task: Optional[asyncio.Task] = None
        self._subscriber_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        logger.info(f"WebSocket connected for job {job_id}")

        # Start (or restart) Redis subscriber if needed
        await self._ensure_subscriber_running()

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.active_connections and websocket in self.active_connections[job_id]:
            self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
            logger.info(f"WebSocket disconnected for job {job_id}")

        # If there are no local listeners, stop subscriber to free resources.
        if not self.active_connections:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._stop_subscriber())
            except RuntimeError:
                # No running loop; safe to ignore.
                pass

    async def broadcast_job_update(self, job_id: str, data: dict):
        """Push a message to all locally-connected WebSocket clients for a job."""
        if job_id in self.active_connections:
            connections = list(self.active_connections[job_id])
            message = json.dumps(data)
            for connection in connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Failed to send WebSocket message: {e}")
                    self.disconnect(connection, job_id)

    async def _redis_subscriber_loop(self):
        """
        Subscribe to Redis pub/sub channels for all active jobs.

        When a worker publishes a job update, this loop receives it
        and forwards it to locally-connected WebSocket clients.
        """
        backoff_seconds = 1

        while True:
            pubsub = None
            try:
                from backend.app.core.redis import get_redis, CHANNEL_PREFIX

                r = await get_redis()
                pubsub = r.pubsub()

                # Subscribe to wildcard pattern for all job channels.
                await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
                logger.info("🔴 Redis pub/sub subscriber started for job updates")
                backoff_seconds = 1

                async for message in pubsub.listen():
                    if message.get("type") != "pmessage":
                        continue

                    # No local subscribers right now; skip fan-out work.
                    if not self.active_connections:
                        continue

                    try:
                        channel = message.get("channel", "")
                        if isinstance(channel, bytes):
                            channel = channel.decode()
                        job_id = channel.replace(CHANNEL_PREFIX, "")

                        data_str = message.get("data", "{}")
                        if isinstance(data_str, bytes):
                            data_str = data_str.decode()
                        data = json.loads(data_str)

                        # Fallback if channel parsing fails for any reason
                        job_id = job_id or str(data.get("job_id") or "")
                        if not job_id:
                            continue

                        # Fan out to local WebSocket connections
                        await self.broadcast_job_update(job_id, data)
                    except Exception as e:
                        logger.error(f"Error processing Redis pub/sub message: {e}")

            except asyncio.CancelledError:
                logger.info("Redis pub/sub subscriber task cancelled")
                break
            except Exception as e:
                logger.error(f"Redis pub/sub subscriber crashed: {e}")
                await asyncio.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 10)
            finally:
                if pubsub is not None:
                    try:
                        await pubsub.punsubscribe()
                    except Exception:
                        pass
                    try:
                        await pubsub.aclose()
                    except Exception:
                        pass

    async def _ensure_subscriber_running(self):
        async with self._subscriber_lock:
            if self._subscriber_task is None or self._subscriber_task.done():
                self._subscriber_task = asyncio.create_task(self._redis_subscriber_loop())

    async def _stop_subscriber(self):
        async with self._subscriber_lock:
            if self._subscriber_task is not None and not self._subscriber_task.done():
                self._subscriber_task.cancel()
                try:
                    await self._subscriber_task
                except asyncio.CancelledError:
                    pass
            self._subscriber_task = None


# Global singleton — used by both the WebSocket endpoint and the
# (optional) in-process fallback path
manager = ConnectionManager()
