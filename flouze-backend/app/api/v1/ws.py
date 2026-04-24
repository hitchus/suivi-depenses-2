import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.redis import get_redis
from app.core.security import decode_access_token

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=4001)
        return

    await websocket.accept()

    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"notify:{user_id}")

    async def _forward():
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])

    async def _drain():
        try:
            async for _ in websocket.iter_text():
                pass
        except WebSocketDisconnect:
            pass

    forward_task = asyncio.create_task(_forward())
    drain_task = asyncio.create_task(_drain())
    try:
        done, pending = await asyncio.wait(
            [forward_task, drain_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        await pubsub.unsubscribe(f"notify:{user_id}")
        await pubsub.aclose()
