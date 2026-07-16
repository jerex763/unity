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

## Session authentication

The MVP API uses Django sessions. `POST /api/auth/login/` accepts `username`,
`password` and an optional `church_id`. Accounts with one active membership are
selected automatically; accounts with multiple active memberships must choose a
church. The response sets a CSRF cookie and stores `active_church_id` in the
session.

- `POST /api/auth/login/` — start a session
- `GET /api/auth/session/` — read the current user and church role
- `POST /api/auth/logout/` — end the session; requires the CSRF header

Role capabilities are defined in `accounts/permissions.py`. They always require
an active membership in the church being checked.

## Church scoping

`ActiveChurchMiddleware` revalidates the session membership on every request and
sets `request.church` plus `request.church_membership`. Invalid or inactive access
is removed from the session.

DRF list and detail views over church-owned models must inherit
`ChurchScopedQuerysetMixin`; it filters before object lookup, so an ID belonging
to another church returns 404. Background jobs, commands and other ORM code must
scope explicitly:

```python
Person.objects.for_church(church)
```

Do not use an unscoped `objects.all()` in a request path. Views requiring a named
role capability should combine `HasActiveChurchMembership` and
`HasChurchCapability`.

## Django Admin

Create the first local administrator, then open <http://localhost:8000/admin/>:

```bash
python manage.py createsuperuser
```

All project models are registered with search and filters. Until the role-based
permissions and church scoping in #4 and #5 land, project admin pages are
superuser-only. As a second layer of protection, non-superuser Person forms omit
`faith_background` and `discipleship_stage` when access is relaxed later.

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
