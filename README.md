# Unity

Church membership + discipleship management app, built by and for our church community. Internal tool first; possible productization later.

**What it does:** a people directory, a newcomer follow-up pipeline, and event signup/check-in that replaces editing numbered lists in WhatsApp group chats.

**What it deliberately does NOT do:** payments (use Tithe.ly/Pushpay links), facial recognition, message sentiment analysis, ethnicity data collection. See [docs/db-model.md](docs/db-model.md) for rationale.

## Progress

| Milestone | Scope | Progress |
|---|---|---|
| [M0 Foundation](https://github.com/jerex763/unity/milestone/1) | Django + React scaffold, models, auth, CI | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/1) |
| [M1 People Directory](https://github.com/jerex763/unity/milestone/2) | Person CRUD, search, profiles, import | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/2) |
| [M2 Events & Check-in](https://github.com/jerex763/unity/milestone/3) | Events, registration, QR check-in | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/3) |
| [M3 Follow-up Queue](https://github.com/jerex763/unity/milestone/4) | FAITH pipeline, interactions, dashboard | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/4) |
| [M4 Groups & Care](https://github.com/jerex763/unity/milestone/5) | Groups, health status, care kanban | ![](https://img.shields.io/github/milestones/progress-percent/jerex763/unity/5) |

Full feature ledger with owners and completion dates: **[docs/features.md](docs/features.md)**
All open work: **[Issues](https://github.com/jerex763/unity/issues)** · grouped by **[Milestones](https://github.com/jerex763/unity/milestones)**

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Django 5 + DRF + Postgres | Admin panel for free, mature auth/permissions |
| Frontend | React (Vite) responsive PWA | No app store; works on any phone browser |
| Auth | Django sessions, role-based | `admin` / `pastor` / `leader` / `member` |

## Repo structure

```
docs/          # db-model.md (schema), features.md (ledger)
backend/       # Django project (coming — issue #1)
frontend/      # React PWA (coming — issue #6)
```

## Getting started

> Scaffold not yet merged. Once #1 and #6 land, this section gets real setup steps (docker-compose, migrate, seed, npm dev). Until then, start from [docs/db-model.md](docs/db-model.md).

## How we work

Read **[CONTRIBUTING.md](CONTRIBUTING.md)** before your first PR. Short version:

1. Pick an unassigned [issue](https://github.com/jerex763/unity/issues), assign yourself
2. Branch `feat/<issue#>-short-slug` off `main`
3. PR referencing the issue (`Closes #N`) — `main` is protected, all changes go through PR
4. After merge: mark your row in [docs/features.md](docs/features.md) — status ✅, your name, date

## Principles

- Every domain table carries `church_id` from day one (multi-tenant insurance)
- Sensitive data minimized and role-gated: pastoral notes are not general staff reading
- Small PRs, one issue each; working software over big-bang branches
