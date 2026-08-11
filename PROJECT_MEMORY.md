# Project Memory

## 2026-08-11 — Learning Loop v1

Статус: принято.

Безопасный контур обучения вне Freeze AI Core:

- `backend/app/learning/` — модели, репозиторий, `LearningService`, `CandidateService`, smoke evaluation.
- Хуки: `DefaultHandoffManager.create_handoff`, `ManagerQueueService.update_status(done)`.
- Публикация KB только через `POST /learning/candidates/{id}/approve` → `KnowledgeRepository.add`.
- Price/stock handoff → только `LearningEvent`, без publishable FAQ-кандидата.
- AI Core не импортирует learning / learning repositories.

## 2026-08-07 — WhatsApp channel (Sprint 17)

Статус: принято.

Production-подключение Meta WhatsApp Cloud API по тому же паттерну, что MAX:

| Режим | Вход | Исходящие |
|-------|------|-----------|
| Webhook | Meta → `GET/POST /channels/whatsapp/webhook` | `HttpWhatsAppTransport` при `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_PHONE_NUMBER_ID` |

Компоненты:

- `WhatsAppChannelAdapter` — simplified + Cloud API payload, route cache `wa_id`
- `integrations/whatsapp/transport.py` — `POST /{version}/{phone_number_id}/messages`
- `channel_adapters/whatsapp_payload.py` — text messages; status callbacks игнорируются (`EVENT_RECEIVED`)
- `GET /channels/whatsapp/webhook` — verify handshake (`WHATSAPP_VERIFY_TOKEN`)

AI Core не знает о WhatsApp. Без credentials outbound остаётся stub (как раньше).

## 2026-08-06 — MAX channel (Sprint 16)

Статус: принято.

Два режима деплоя:

| Режим | Вход | Исходящие ответы |
|-------|------|------------------|
| Прямой webhook | MAX → `POST /channels/max/webhook` (Python) | Python `HttpMaxTransport` (`MAX_BOT_TOKEN`) |
| Go bridge | MAX polling → `bot_iwt_max/cmd/platform-bridge` → Python webhook | Python при `PLATFORM_SENDS_REPLIES=true` (default); иначе Go sender |

Компоненты Python:

- `MaxChannelAdapter` — normalize simplified + native MAX payload, route cache `user_id`/`chat_id`
- `integrations/max/transport.py` — `POST /messages` с `Authorization: <token>`
- `channel_adapters/max_payload.py` — парсинг `message_created`, skip `message_callback`

Standalone Go-бот (каталог JSON, FSM, SQLite-заявки) — deprecated в пользу AI pipeline + Manager Queue.

Callbacks в bridge только ACK, в AI pipeline не идут.

## 2026-08-04 — Website Live API = Bitrix REST webhook

Статус: принято.

Источник товарных данных для Website Provider:

- Base URL: `https://iwt.ru/rest/1/<webhook>/`
- Auth: токен в пути URL (`WEBSITE_API_AUTH_MODE=none`)
- Каталог товаров: `iblockId=86` (`WEBSITE_CATALOG_IBLOCK_ID`)

Идентификаторы товара:

- `code` → `Product.sku` (основной внешний id / артикул)
- `xmlId` → 1С обмен (хранится в characteristics, участвует в поиске)
- `id` → внутренний Bitrix id (`Product.id`)

Поиск клиента резолвится по: name (`%name`), code, xmlId, Bitrix id.

Цена: отдельный метод `catalog.price.list` (в `catalog.product.get` цены нет).
Цена попадает в `confirmed_fields` только если пришла из price.list.

Правило озвучивания цены (обязательное):

- Если цена получена из `catalog.price.list` → поле `price` в `confirmed_fields` →
  AI Validator **разрешает** озвучивать цену клиенту.
- Если цена не пришла → `price` **не** подтверждена →
  Validator возвращает `NEEDS_DATA` → Decision Router создаёт handoff менеджеру.
- Выдуманная или «угаданная» цена без `confirmed_fields` запрещена.

## 2026-08-04 — Источники данных: Bitrix vs Knowledge Base

Статус: принято.

Разделение ответственности (не хранить delivery/payment/warranty в Bitrix):

| Данные | Источник |
|--------|----------|
| Товар | Bitrix (`catalog.product.*`) |
| Цена | Bitrix (`catalog.price.list`) |
| Наличие | Bitrix (`available` / `quantity`) |
| Характеристики | Bitrix (product properties) |
| Оплата | Knowledge Base |
| Доставка | Knowledge Base |
| Гарантия | Knowledge Base |
| Компания | Knowledge Base |
| FAQ | Knowledge Base |

Причины:

- менеджеры меняют тексты без программистов;
- не нужно менять Bitrix под контент;
- удобно расширять инструкции / FAQ / гарантии.

Реализация:

- `SourceSelector` агрегирует Knowledge Base + Website/Bitrix provider;
- Bitrix client не отдаёт delivery/payment/warranty/contacts (NotFound → пусто у WebsiteProvider);
- контент оплаты/доставки/гарантии/FAQ берётся только из Knowledge Base.

## 2026-08-03 — Architecture Freeze v2.1

Статус: принято.

Решение:

- Объявить Architecture Freeze v2.1.
- Tool Registry пока остается только контрактом.
- Error Logger и Audit Log не выделяются в отдельные компоненты на MVP; используется единый LoggingService.
- Session Manager и Conversation Manager могут иметь одну MVP-реализацию ConversationStateService при сохранении двух интерфейсов.
- Decision Router остается тонким маршрутизатором готового ProcessingResult.
- Source Selector только выбирает источники и не содержит AI-ranking, RAG, validation или бизнес-решений.

Правило:

Новые архитектурные изменения запрещены до появления реальной причины в коде. Исключение допускается только для устранения критической проблемы или значительного упрощения системы без нарушения существующих контрактов.

## 2026-08-03 — Confirmed Fields Rule

Статус: принято.

Решение:

В v2 все новые источники данных обязаны явно заполнять `confirmed_fields`.

Пустой `confirmed_fields` не является подтверждением данных.

Реализация:

- тип: `set[str]`;
- проверка: `field_name in confirmed_fields`;
- пустой set никогда не подтверждает поля;
- наличие значения вроде `price=1000` без `"price"` в `confirmed_fields` не даёт AI права сообщать цену.

Причина:

AI Validator должен отличать наличие значения в объекте от факта, что это значение подтверждено источником.

## 2026-08-03 — Knowledge Search Responsibility

Статус: принято.

Решение:

`KnowledgeSearchService` никогда не принимает решения, какой источник "лучше".

Он только возвращает кандидатов.

Выбор делает `SourceSelector`.

Причина:

Разделить поиск кандидатов и выбор подтверждённых источников, чтобы не нарушать SRP и не смешивать Knowledge Base с Source Selector.
