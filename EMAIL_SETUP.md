# Email → /inbox (Sprint 18)

Режим: **черновик AI + ответ менеджера**. Автоответов клиенту нет.

## Поток

1. Worker читает `UNSEEN` из IMAP (`iwt.iwt@ya.ru`).
2. Письмо проходит AI pipeline.
3. Политика email всегда кладёт заявку в `manager_queue` (черновик в `ai_response`).
4. Менеджер видит заявку на `https://api.iwt.ru/inbox`.
5. При «Готово» с текстом ответа письмо уходит по SMTP отправителю.

## Yandex

1. Включите IMAP в настройках почты Yandex.
2. Создайте **пароль приложения** для почты (не обычный пароль входа).
3. Добавьте в `.env` на VPS:

```env
EMAIL_ENABLED=true
EMAIL_IMAP_HOST=imap.yandex.ru
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=smtp.yandex.ru
EMAIL_SMTP_PORT=465
EMAIL_USERNAME=iwt.iwt@ya.ru
EMAIL_PASSWORD=пароль_приложения
EMAIL_FROM=iwt.iwt@ya.ru
EMAIL_POLL_SECONDS=60
EMAIL_MAILBOX=INBOX
```

## Деплой

```bash
cd /opt/iwt-ai-sales-platform
# обновить код + .env
docker compose -f docker-compose.prod.yml up -d --build api email-worker
docker compose -f docker-compose.prod.yml logs -f email-worker
```

Сервис `email-worker` должен писать `Email worker started`. Без `EMAIL_ENABLED=true` и пароля worker завершится с ошибкой.

## Проверка

1. Отправьте тестовое письмо на `iwt.iwt@ya.ru`.
2. Через ~1 минуту заявка появится в `/inbox` (канал Email).
3. Отредактируйте черновик → «Готово» → ответ уйдёт на From письма.

Ручной webhook (без IMAP):

```bash
curl -sS -X POST https://api.iwt.ru/channels/email/webhook \
  -H 'Content-Type: application/json' \
  -d '{"from":"client@example.com","subject":"Тест","body":"Нужна консультация","message_id":"<test-1@example.com>"}'
```
