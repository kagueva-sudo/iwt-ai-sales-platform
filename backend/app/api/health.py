from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine


router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check() -> JSONResponse:
    settings = get_settings()
    checks = {
        "app": "ok",
        "environment": settings.app_env,
        "database": "unknown",
    }

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready", "checks": checks})
    except Exception as exc:
        checks["database"] = "error"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "checks": checks, "error": exc.__class__.__name__},
        )
