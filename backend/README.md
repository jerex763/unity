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

## One-off people CSV import

Use the **Import CSV** action on the People admin page, or run:

```bash
python manage.py import_people_csv ../docs/person-import-template.csv \
  --church-id 1 --dry-run
```

Remove `--dry-run` only after the preview succeeds. Imports are atomic: any bad
row rejects the entire file and reports its source row number. Re-running a file
updates a unique email match, then a unique phone match, then a unique full-name
match; columns omitted from a file are left unchanged. The supported headings
are listed in [`docs/person-import-template.csv`](../docs/person-import-template.csv),
and interests use semicolons within one CSV cell.

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

## Security audit trail

Important authentication, confidential-care access, person changes, membership
role/access changes and CSV exports create append-only audit events. Events store
identifiers and approved operational metadata only, never changed field values or
secrets. See [the retention policy](../docs/audit-retention.md) before production
use.

## Consent records

`GET /api/people/<id>/consent/` returns the latest consent decision, or an
explicit `unknown` state when no decision has been recorded. Authorized admins
and pastors can `POST` a granted or declined decision; a later POST creates an
immutable correction linked to the previous record instead of overwriting it.
Creating or importing a person never creates consent automatically.

## Person directory API

- `GET/POST /api/people/` — list visible people or create a person
- `GET/PUT/PATCH /api/people/<id>/` — read or update a visible person
- `GET/POST /api/people/<id>/relationships/` — list or add visible
  friend/family/spouse/guardian links
- `DELETE /api/people/<id>/relationships/<relationship-id>/` — remove a
  visible relationship link
- `GET/POST /api/events/` — list church events or create an event
- `GET/PUT/PATCH/DELETE /api/events/<id>/` — read or manage an event
- `GET/POST /api/events/<id>/registrations/` — view the permitted roster or
  register a visible person (members default to their linked Person)
- `POST /api/events/<id>/registrations/<registration-id>/cancel/` — cancel a
  permitted registration while preserving its history
- `POST /api/events/<id>/walk-ins/` — ministry-worker quick-add for a minimal
  visitor plus manual walk-in attendance
- `POST /api/events/<id>/registrations/<registration-id>/check-in/` — set or
  undo manual attendance (`{"checked_in": true|false}`)

Admins and pastors see the active church directory. Leaders see active members
of groups they lead or co-lead. Members can read only their linked Person and
cannot write. `faith_background` and `discipleship_stage` are absent unless the
role is pastor or admin; member responses also omit staff `notes`.

Routine `DELETE` is intentionally unavailable. Use the documented deactivate,
anonymize or reason-gated hard-delete lifecycle instead.
