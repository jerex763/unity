# Contributing to Unity

## Workflow

1. **Claim an issue.** Pick an unassigned one from [Issues](https://github.com/jerex763/unity/issues), assign yourself, move it along. Don't start work without an issue — if something's missing, open one first.
2. **Branch off `main`:** `feat/<issue#>-short-slug` (e.g. `feat/8-person-api`). Fixes: `fix/<issue#>-slug`.
3. **Small, focused PRs.** One issue per PR. Reference it in the description: `Closes #8`.
4. **`main` is protected** — no direct pushes. Every change lands via PR.
5. **After your PR merges:**
   - The issue auto-closes (via `Closes #N`) — GitHub records who and when
   - Update your row in [docs/features.md](docs/features.md): status → ✅, add your GitHub handle and merge date

## Commit messages

```
<type>: <description>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`

Example: `feat: person search endpoint with role-gated fields`

## Code standards

- **Backend:** Python 3.12+, `black` + `ruff` clean, type annotations on function signatures. Tests with `pytest` for anything with logic (target: every API endpoint has at least happy-path + permission tests).
- **Frontend:** `prettier` + `eslint` clean. Components in `PascalCase`, hooks prefixed `use`.
- **Schema changes:** update [docs/db-model.md](docs/db-model.md) in the same PR as the migration. The doc and the models must never drift.

## Definition of done

- [ ] CI green (lint + tests)
- [ ] Sensitive-data rules respected (see db-model.md privacy notes — pastoral fields are pastor/admin only)
- [ ] Every sensitive endpoint has both allow and deny permission tests
- [ ] Cross-church access is denied even when an object ID is known
- [ ] Sensitive or destructive actions are included in the audit design
- [ ] Screenshots, fixtures and tests use fictional or safely anonymized data only
- [ ] features.md row updated
- [ ] No secrets/credentials in code — use `.env`

## Questions / design changes

Anything that changes the DB schema or cuts/adds scope: open an issue and discuss before coding. Small stuff: just ask in the group chat.

If the team is unsure what to build next, use [docs/delivery-plan.md](docs/delivery-plan.md), the current milestone and the `next` backlog instead of relying on memory.
