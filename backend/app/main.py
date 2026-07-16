from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.messages import router as messages_router
from app.core.config import get_settings
from app.core.logging import configure_logging


settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(health_router)
app.include_router(messages_router)
