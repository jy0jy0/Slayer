"""Health check endpoint."""

from fastapi import APIRouter
from slayer.db.session import is_db_available

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "db": "connected" if is_db_available() else "unavailable"}
