# AI Sales Platform iwt.ru

Backend foundation for the commercial AI Sales Platform.

## Sprint 1 Scope

- FastAPI backend
- Docker and Docker Compose
- PostgreSQL configuration
- AI Core skeleton
- AI Validator skeleton
- Handoff mechanism
- Provider interfaces for products, customers, and CRM
- Structured API schemas
- Basic logging and env-based configuration

## Not Included Yet

- Redis
- Message queues
- RBAC / SSO
- Admin Panel
- Real integrations with 1C, Bitrix24, or Email (MAX и WhatsApp — см. ниже)
- Advanced monitoring infrastructure

## Local Run

```bash
cp .env.example .env
docker compose up --build
```

API health check:

```bash
curl http://localhost:8000/health
```

Readiness check with database connection:

```bash
curl http://localhost:8000/health/ready
```

## Environment Variables

Required variables:

- `APP_NAME` - application name.
- `APP_ENV` - environment name: `local`, `staging`, or `production`.
- `DEBUG` - FastAPI debug mode.
- `LOG_LEVEL` - logging level.
- `API_PORT` - public API port on the host.
- `POSTGRES_DB` - PostgreSQL database name.
- `POSTGRES_USER` - PostgreSQL user.
- `POSTGRES_PASSWORD` - PostgreSQL password.
- `POSTGRES_PORT` - public PostgreSQL port on the host.
- `DATABASE_URL` - SQLAlchemy PostgreSQL connection string.
- `OPENAI_API_KEY` - OpenAI API key.
- `OPENAI_MODEL` - OpenAI model name.
- `CATALOG_API_URL` - future iwt.ru catalog REST API base URL.
- `CATALOG_API_KEY` - future catalog API key.
- `CATALOG_TIMEOUT` - catalog API timeout in seconds.
- `IWT_STORE_BASE_URL` - public storefront base (default `https://www.iwt.ru`); HTML catalog search, no Bitrix needed.
- `IWT_STORE_ENABLED` - enable/disable public catalog provider (default `true`).
- `WEBSITE_API_URL` - optional Bitrix inbound webhook fallback, e.g. `https://iwt.ru/rest/1/<webhook>`.
- `WEBSITE_API_KEY` - unused for Bitrix webhook auth (token is in the URL).
- `WEBSITE_API_TIMEOUT` - website API timeout in seconds.
- `WEBSITE_API_AUTH_MODE` - `none` for Bitrix webhook; also supports `bearer` / `api_key`.
- `WEBSITE_CATALOG_IBLOCK_ID` - Bitrix catalog iblock id (default `86` for Товары 1С).
- `MAX_BOT_TOKEN` - MAX bot token for outbound messages via MAX API.
- `MAX_API_BASE_URL` - MAX API base URL (default `https://platform-api2.max.ru`).
- `MAX_API_TIMEOUT` - MAX API timeout in seconds.
- `WHATSAPP_ACCESS_TOKEN` - Meta WhatsApp Cloud API access token.
- `WHATSAPP_PHONE_NUMBER_ID` - WhatsApp phone number id for outbound sends.
- `WHATSAPP_VERIFY_TOKEN` - token for Meta webhook verification (`GET /channels/whatsapp/webhook`).
- `WHATSAPP_API_VERSION` - Graph API version (default `v21.0`).

### MAX channel

Webhook endpoint: `POST /channels/max/webhook`

Два режима деплоя:

1. **Прямой** — MAX шлёт webhook на Python API; задайте `MAX_BOT_TOKEN` в `.env`.
2. **Через Go bridge** — polling в `bot_iwt_max/cmd/platform-bridge` форвардит события в Python;
   при `PLATFORM_SENDS_REPLIES=true` ответы отправляет Python (нужен `MAX_BOT_TOKEN` на стороне платформы).

Товары/цены — публичный каталог iwt.ru (`IWT_STORE_*`), FAQ/доставка/оплата — Knowledge Base. Bitrix webhook опционален.

### WhatsApp channel

Endpoints:

- `GET /channels/whatsapp/webhook` — Meta verify handshake (`WHATSAPP_VERIFY_TOKEN`)
- `POST /channels/whatsapp/webhook` — inbound Cloud API / simplified payloads

Задайте `WHATSAPP_ACCESS_TOKEN` и `WHATSAPP_PHONE_NUMBER_ID` для исходящих ответов через Graph API.
Status callbacks без текста принимаются как `EVENT_RECEIVED` без запуска pipeline.

Пошаговый запуск (Timeweb HTTPS + Meta): см. [`WHATSAPP_SETUP.md`](WHATSAPP_SETUP.md).
Проверка `.env`: `python backend/scripts/check_whatsapp.py`.

## Learning Loop v1

Контур обучения **вне AI Core**: handoff / закрытие кейса менеджером → `LearningEvent` + опциональный `KnowledgeCandidate` → ручной approve/reject. AI **не пишет** в Knowledge Base сам; автопубликации нет.

Endpoints (внутренний MVP API без RBAC):

- `GET /learning/candidates`
- `GET /learning/candidates/{id}`
- `POST /learning/candidates/{id}/approve` — body `{ "reviewed_by": "..." }`
- `POST /learning/candidates/{id}/reject` — body `{ "reviewed_by": "...", "reason": "..." }`

Статусы кандидата: `pending` → `approved` | `rejected`.

Правила:

- Для `PRICE_UNKNOWN` / `AVAILABILITY_UNKNOWN` создаётся только событие, без кандидата на FAQ-цену.
- Approve публикует FAQ (`category=learning`) **без** `price` / `stock_qty` / `delivery_terms` в `confirmed_fields`.
- Dynamic commercial facts (цена/остаток) — только из Bitrix / live API, не из старых QA.
- Датасеты: `knowledge/learning/customer_qa.jsonl`, `knowledge/learning/evaluation_dataset.jsonl` (не в system prompt).

При `PATCH /manager-queue/{id}/status` со `status=done` можно передать опциональное `manager_answer` — оно попадёт в pending-кандидата.

## Ubuntu 24.04 Deployment

1. Install Docker Engine and Docker Compose plugin:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

2. Clone or upload the project to the server:

```bash
cd /opt
sudo git clone <REPOSITORY_URL> iwt-ai-sales-platform
cd /opt/iwt-ai-sales-platform
```

3. Create production environment file:

```bash
cp .env.production.example .env
nano .env
```

Set strong values for:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `OPENAI_API_KEY`

The password in `DATABASE_URL` must match `POSTGRES_PASSWORD`.

4. Start services:

```bash
sudo docker compose up -d --build
```

5. Check status:

```bash
sudo docker compose ps
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready
```

6. View logs:

```bash
sudo docker compose logs -f api
sudo docker compose logs -f db
```

7. Update deployment:

```bash
git pull
sudo docker compose up -d --build
```

Production notes:

- Do not commit `.env`.
- Use a firewall and expose only required ports.
- Put Nginx/HTTPS in front of the API before public access.
- Back up the `postgres_data` volume before upgrades.

## Tests

```bash
cd backend
python -m pytest
```
