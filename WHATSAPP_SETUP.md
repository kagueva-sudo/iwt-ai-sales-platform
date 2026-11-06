# WhatsApp Cloud API — запуск для IWT

Код канала уже в платформе. Боевой приём сообщений: **VPS Timeweb + `https://api.iwt.ru`**.

Сайт `https://iwt.ru/` — магазин Bitrix, не этот API. Поддомен `api.iwt.ru` должен смотреть на **отдельный** VPS с Docker, не на витрину.

Webhook Meta:

```text
https://api.iwt.ru/channels/whatsapp/webhook
```

Verify token: `iwt-wa-verify-9f3c2a7b`

---

## Шаг A. VPS в Timeweb

Рабочий сервер: **Wild Pheasant**, IPv4 **`72.56.85.214`** (2 CPU / 2 ГБ / 50 ГБ). Это не витрина `iwt.ru` (`185.114.245.69`).

SSH с компьютера открыт (порт 22). Порты 80/443 пока закрыты — откроются, когда запустим Caddy.

В фаерволе Timeweb откройте **22, 80, 443**. Порт 8000 наружу не открывайте.

Пришлите IP, если нужна проверка с нашей стороны.

## Шаг B. DNS для `api.iwt.ru`

Там, где управляется домен `iwt.ru` (Timeweb / REG.RU / другой DNS):

| Тип | Имя | Значение |
|-----|------|----------|
| A | `api` | IP VPS из шага A |

Подождите 5–30 минут. Проверка с ПК:

```powershell
nslookup api.iwt.ru
```

Должен вернуться IP VPS, не магазина.

## Шаг C. Установка на сервер

По SSH (PowerShell):

```bash
ssh root@IP_VPS
```

На сервере:

```bash
apt update && apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
cd /opt
git clone <URL_РЕПОЗИТОРИЯ> iwt-ai-sales-platform
cd /opt/iwt-ai-sales-platform
cp .env.production.example .env
nano .env
```

В `.env` на сервере обязательно:

- сильный `POSTGRES_PASSWORD` (тот же в `DATABASE_URL`)
- `OPENAI_API_KEY`, `WEBSITE_API_URL`, `MAX_BOT_TOKEN`
- `WHATSAPP_ACCESS_TOKEN` и `WHATSAPP_PHONE_NUMBER_ID=143890192837208`
- `WHATSAPP_VERIFY_TOKEN=iwt-wa-verify-9f3c2a7b`

Запуск:

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

Caddy сам получит HTTPS-сертификат для `api.iwt.ru` (нужны шаг B и порты 80/443).

Проверка с телефона или другого ПК:

```bash
curl https://api.iwt.ru/health
curl "https://api.iwt.ru/channels/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=iwt-wa-verify-9f3c2a7b&hub.challenge=ok"
```

Второй запрос должен вернуть `ok`.

## Шаг D. Webhook в Meta

В приложении IWT_Bot → **Шаг 2. Настройка рабочей среды**:

- URL обратного вызова: `https://api.iwt.ru/channels/whatsapp/webhook`
- Подтверждение маркера: `iwt-wa-verify-9f3c2a7b`
- Сертификат клиента — выкл.
- **Проверить и сохранить**
- Подписка: **messages**

## Шаг E. Проверка бота

С WhatsApp, который добавлен как тестовый получатель, напишите на тестовый номер Meta (`+1 555-607-2832`). Должен ответить AI pipeline (как в MAX).

Временный токен из кабинета живёт ограниченно. Для боя потом — токен **системного пользователя**.

---

## Локальная проверка `.env` (ваш ПК)

```bash
cd backend
.venv\Scripts\python.exe scripts\check_whatsapp.py
```
