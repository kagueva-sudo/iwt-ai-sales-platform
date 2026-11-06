"""Print WhatsApp channel readiness without leaking secrets."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.integrations.whatsapp.config import is_whatsapp_configured  # noqa: E402


def _masked(value: str) -> str:
    text = value.strip()
    if not text:
        return "(пусто)"
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}…{text[-4:]} (len={len(text)})"


def main() -> int:
    settings = get_settings()
    outbound = is_whatsapp_configured()
    verify = bool(settings.whatsapp_verify_token.strip())
    print("WhatsApp outbound (token + phone id):", "OK" if outbound else "НЕТ")
    print("Verify token задан:", "OK" if verify else "НЕТ")
    print("WHATSAPP_PHONE_NUMBER_ID:", _masked(settings.whatsapp_phone_number_id))
    print("WHATSAPP_ACCESS_TOKEN:", _masked(settings.whatsapp_access_token))
    print("WHATSAPP_VERIFY_TOKEN:", _masked(settings.whatsapp_verify_token))
    print("API version:", settings.whatsapp_api_version or "v21.0")
    print()
    if not verify:
        print("Задайте WHATSAPP_VERIFY_TOKEN в .env")
        return 1
    if not outbound:
        print("Для ответов клиенту задайте WHATSAPP_ACCESS_TOKEN и WHATSAPP_PHONE_NUMBER_ID.")
        print("Webhook verify при этом уже возможен, если API доступен по HTTPS.")
        return 2
    print("Локальный конфиг исходящих сообщений готов. Нужен публичный HTTPS webhook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
