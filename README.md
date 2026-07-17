# Unity

Church membership + discipleship management app, built by and for our church community. Internal tool first; possible productization later.

**What it does:** a people directory, a newcomer follow-up pipeline, and event signup/check-in that replaces editing numbered lists in WhatsApp group chats.

**What it deliberately does NOT do:** payments (use Tithe.ly/Pushpay links), facial recognition, message sentiment analysis, ethnicity data collection. See [docs/db-model.md](docs/db-model.md) for rationale.

## Progress

| Milestone | Scope | Progress |
|---|---|---|
| [M0 Foundation](https://github.com/jerex763/unity/milestone/1) | Scaffold, models, auth, tenancy, privacy foundations, backup, CI | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/1) |
| [M1 People Directory](https://github.com/jerex763/unity/milestone/2) | Person CRUD, search, profiles, import | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/2) |
| [M2 Events & Check-in](https://github.com/jerex763/unity/milestone/3) | Events, registration, manual check-in first; QR later | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/3) |
| [M3 Follow-up Queue](https://github.com/jerex763/unity/milestone/4) | Follow-up pipeline, interactions, dashboard | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/4) |
| [Pilot Release Gate](https://github.com/jerex763/unity/milestone/6) | One controlled end-to-end trial, feedback and restore test | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/6) |
| [M4 Groups & Care](https://github.com/jerex763/unity/milestone/5) | Groups, health status, care kanban | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/5) |

Full feature ledger with owners and completion dates: **[docs/features.md](docs/features.md)**
All open work: **[Issues](https://github.com/jerex763/unity/issues)** · grouped by **[Milestones](https://github.com/jerex763/unity/milestones)**

Start with **[docs/delivery-plan.md](docs/delivery-plan.md)** for what to do now, next and later. The full 13-module vision and what's deferred/cut remains in **[docs/roadmap.md](docs/roadmap.md)**. Frontend visual language: **[docs/design.md](docs/design.md)**.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Django 5 + DRF + Postgres | Admin panel for free, mature auth/permissions |
| Frontend | React (Vite) responsive PWA | No app store; works on any phone browser |
| Auth | Django sessions, role-based | `admin` / `pastor` / `leader` / `member` |

## Repo structure

```
docs/          # delivery plan, schema, feature ledger, full vision and UI direction
backend/       # Django + DRF API
frontend/      # React + TypeScript responsive PWA
```

## Getting started

The backend requires Python 3.12+ and Postgres. From the repository root:

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

The API health check is available at <http://localhost:8000/api/health/>.

In a second terminal, start the frontend with Node.js 22+:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

The app is available at <http://localhost:5173>; development `/api` requests are
proxied to Django. See [frontend/README.md](frontend/README.md) for quality checks
and production builds.

The authentication foundation uses a custom `User` from its first migration and
stores church-specific roles in `ChurchMembership`. See
[ADR 0001](docs/adr/0001-authentication-and-church-membership.md) before adding
authentication or tenant-scoped features.

See [backend/README.md](backend/README.md) for configuration, testing and production
settings. Operational safeguards are documented in the
[backup/restore runbook](docs/backup-restore-runbook.md) and
[person data lifecycle](docs/person-data-lifecycle.md). Authorization rules are
defined in the [permission and privacy matrix](docs/permission-matrix.md).

## How we work

Read **[CONTRIBUTING.md](CONTRIBUTING.md)** before your first PR. Short version:

1. Pick an unassigned [issue](https://github.com/jerex763/unity/issues), assign yourself
2. Branch `feat/<issue#>-short-slug` off `main`
3. PR referencing the issue (`Closes #N`) — `main` is protected, all changes go through PR
4. After merge: mark your row in [docs/features.md](docs/features.md) — status ✅, your name, date

## Principles

- Every domain table carries `church_id` from day one (multi-tenant insurance)
- Sensitive data minimized and role-gated: pastoral notes are not general staff reading
- No real member data before the M0 privacy, audit and restore exit gate passes
- Small PRs, one issue each; working software over big-bang branches
