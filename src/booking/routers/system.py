from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from booking.core.config import get_settings
from booking.db.engine import get_engine, ping_db

router = APIRouter(tags=["system"])

EngineDep = Annotated[AsyncEngine, Depends(get_engine)]


@router.get("/health")
async def health(engine: EngineDep) -> JSONResponse:
    settings = get_settings()
    db_ok = await ping_db(engine)
    body = {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "version": settings.app_version,
    }
    code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=body)
