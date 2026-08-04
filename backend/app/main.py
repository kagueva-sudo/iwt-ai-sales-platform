from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.email_webhook import router as email_webhook_router
from app.api.gateway import router as gateway_router
from app.api.health import router as health_router
from app.api.manager_queue import router as manager_queue_router
from app.api.max_webhook import router as max_webhook_router
from app.api.messages import router as messages_router
from app.api.website import router as website_router
from app.api.whatsapp_webhook import router as whatsapp_webhook_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.init_db import init_db


settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
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
