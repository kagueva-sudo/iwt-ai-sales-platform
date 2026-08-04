# PROJECT_ROADMAP — AI Sales Platform iwt.ru

| Поле | Значение |
|------|----------|
| Архитектура | Architecture Freeze v2.2 |
| Текущая позиция | Sprint 15 завершён → далее Sprint 16 |
| Обновлено | 2026-08-04 |

Связанные документы: `PROJECT_SPEC.md`, `DEVELOPMENT_RULES.md`, `PROJECT_MEMORY.md`, `ACCEPTANCE_CRITERIA.md`, `README.md`.

---

## Статус спринтов

✔ Sprint 1

✔ Sprint 2

✔ Sprint 3

✔ Sprint 4

✔ Sprint 5

✔ Sprint 6

✔ Sprint 7

✔ Sprint 8

✔ Sprint 9

✔ Sprint 10

✔ Sprint 11

✔ Sprint 12

✔ Sprint 13

✔ Sprint 14

✔ Sprint 14.1

✔ Sprint 15 Website Live API

⬜ Sprint 16 MAX

⬜ Sprint 17 WhatsApp

⬜ Sprint 18 Email

⬜ Sprint 19 Prompt Optimization

⬜ Sprint 20 Knowledge UI

---

## Цель roadmap

Зафиксировать порядок реализации коммерческой AI Sales Platform для iwt.ru:

- единый `AI Core` для всех каналов;
- ответы только на подтверждённых данных (`confirmed_fields`);
- handoff сложных случаев во внутреннюю очередь менеджеров;
- подключение каналов и источников без изменения `AI Core`.

---

## Архитектурный пайплайн (freeze)

```text
Channels → Adapters → Gateway → ConversationState → SourceSelector
→ PromptBuilder → AICore → LLM → Validator → ProcessingResult
→ DecisionRouter → ResponseSender / HandoffManager / LoggingService
```

Жёсткие правила:

- `AI Core` не знает каналы, CRM, handoff, router и конкретные интеграции;
- `SourceSelector` выбирает источники; `KnowledgeSearchService` только возвращает кандидатов;
- пустой `confirmed_fields` ≠ подтверждение;
- без RAG / embeddings / vector DB, пока это явно не запрошено;
- без Redis, очередей сообщений, RBAC, SSO и Admin Panel в текущем MVP.

---

## Справка: завершённые спринты (1–14.1)

| Sprint | Название |
|--------|----------|
| 1 | Architecture Contracts Foundation |
| 2 | AI Gateway + единая точка входа |
| 3 | Website Provider contract |
| 4 | Website Provider API-ready Layer |
| 5 | Knowledge Base Foundation |
| 6 | AI Core v2 Foundation |
| 7 | Decision Router + Handoff Manager |
| 8 | Gateway Freeze Wiring + MAX (adapter foundation) |
| 9 | Email + WhatsApp Channels (adapter foundation) |
| 10 | Website Channels |
| 11 | Manager Queue API |
| 12 | Manager Queue Persistence |
| 13 | Sessions + Conversations Persistence |
| 14 | LoggingService Persistence + Knowledge Content Foundation |
| 14.1 | Knowledge Search Hardening |

Ранее (до v2 engineering track): Foundation Sprint 1 / 1.1 / 1.2, Catalog 2A, Architecture Alignment 0 / 0.1, Freeze v2.1–v2.2.

---

## План: следующие спринты (15–20)

| Sprint | Название | Фокус | Статус |
|--------|----------|-------|--------|
| 15 | Website Live API | Live HttpWebsiteTransport, auth, search/products, confirmed_fields | ✔ |
| 16 | MAX | Production-подключение канала MAX | ⬜ |
| 17 | WhatsApp | Production-подключение WhatsApp | ⬜ |
| 18 | Email | Production-подключение Email | ⬜ |
| 19 | Prompt Optimization | Улучшение Prompt Builder / политик без смены архитектуры | ⬜ |
| 20 | Knowledge UI | UI для управления Knowledge Base | ⬜ |

Вне текущего плана (бэклог):

- CRM Adapter (Bitrix24 / иное);
- Redis / message queues;
- RBAC / SSO;
- Admin Panel;
- RAG / embeddings / vector search;
- расширенная аналитика и мониторинг.

---

## Правила планирования спринтов

1. Один спринт = одна чёткая цель и проверяемый результат.
2. Не менять Architecture Freeze без причины из `DEVELOPMENT_RULES.md`.
3. Не трогать `AI Core` ради интеграции канала или источника данных.
4. Новый компонент — только если решает текущую проблему, не «на будущее».
5. После спринта: тесты зелёные + запись в `PROJECT_MEMORY.md` при архитектурных решениях.
6. Обновлять чеклист статуса в начале этого файла при старте/завершении спринта.
