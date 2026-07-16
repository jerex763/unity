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
python manage.py check
python manage.py runserver
```

Open <http://localhost:8000/api/health/> to verify the application is running.

## Migration gate

This scaffold intentionally defines no project models or migrations. Do not run
initial project migrations against a shared or production database until
[Issue #26](https://github.com/jerex763/unity/issues/26) has defined the minimal
custom user model and `ChurchMembership`. Django's user model is difficult to
replace after tables have been created. Any local database created before #26
lands must be treated as disposable.

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
