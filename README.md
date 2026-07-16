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
- Real integrations with 1C, Bitrix24, MAX, WhatsApp, or Email
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

## Tests

```bash
cd backend
python -m pytest
```
