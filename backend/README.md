# Unity backend

Django 5 and Django REST Framework scaffold for Unity.

## Local setup

Requirements: Python 3.12+ and Postgres 16 (the root `compose.yaml` provides a
local database).

```bash
docker compose up -d db
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
python manage.py migrate
python manage.py check
python manage.py runserver
```

Open <http://localhost:8000/api/health/> to verify the application is running.

## Authentication foundation

Unity uses `accounts.User` as its custom user model from the first migration.
Church access and roles live in `ChurchMembership`, not on the user. `Person`
records remain separate from login identities. Read
[ADR 0001](../docs/adr/0001-authentication-and-church-membership.md) before
changing authentication or tenancy.

## Configuration

Development uses `config.settings.dev`; production uses `config.settings.prod`.
Both read `backend/.env` when present, while real environment variables take
precedence.

| Variable | Development default | Production |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` | set to `config.settings.prod` |
| `DJANGO_SECRET_KEY` | unsafe local fallback | required, strong and unique |
| `DJANGO_DEBUG` | `true` | must be `false` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | required hostnames |
| `DATABASE_URL` | local Postgres URL | required Postgres URL |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | HTTPS origins when needed |
| `DJANGO_SECURE_SSL_REDIRECT` | `true` in production | disable only behind infrastructure that handles it safely |

Production settings enable secure cookies, HSTS, SSL redirect and proxy HTTPS
header handling. Run deployment checks before release:

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check --deploy
```

## Quality checks

```bash
ruff check .
black --check .
pytest
python manage.py check
```

Tests use an in-memory SQLite database so scaffold checks do not require a local
Postgres process. Runtime development and production settings use Postgres.
