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
- `WEBSITE_API_URL` - future website API base URL.
- `WEBSITE_API_KEY` - future website API key.
- `WEBSITE_API_TIMEOUT` - website API timeout in seconds.

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
