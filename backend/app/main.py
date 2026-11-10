from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.email_webhook import router as email_webhook_router
from app.api.gateway import router as gateway_router
from app.api.health import router as health_router
from app.api.learning import router as learning_router
from app.api.manager_queue import router as manager_queue_router
from app.api.max_webhook import router as max_webhook_router
from app.api.messages import router as messages_router
from app.api.website import router as website_router
from app.api.whatsapp_webhook import router as whatsapp_webhook_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.init_db import init_db
from app.services.knowledge_loader import default_knowledge_dir, seed_knowledge_from_dir


settings = get_settings()
configure_logging(settings.log_level)

STATIC_DIR = Path(__file__).resolve().parent / "static"
INBOX_INDEX = STATIC_DIR / "inbox" / "index.html"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    # Optional seed: `knowledge/{faq,delivery,...}/*.json`.
    await seed_knowledge_from_dir(default_knowledge_dir())
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.include_router(health_router)
app.include_router(gateway_router)
app.include_router(messages_router)
app.include_router(max_webhook_router)
app.include_router(email_webhook_router)
app.include_router(whatsapp_webhook_router)
app.include_router(website_router)
app.include_router(manager_queue_router)
app.include_router(learning_router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def disable_static_cache(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/") or request.url.path.rstrip("/") == "/inbox":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/inbox", include_in_schema=False)
@app.get("/inbox/", include_in_schema=False)
async def manager_inbox() -> FileResponse:
    """Manager-facing inbox UI over existing /manager-queue API."""
    return FileResponse(INBOX_INDEX)
