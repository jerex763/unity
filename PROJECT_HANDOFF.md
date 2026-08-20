# Unity project handoff and operating guide

Last verified: **2026-08-20 (Australia/Sydney)**

This is the first document to read when starting a new Unity chat or work
session. It records the current state and operating rules so the team does not
need to replay conversation history. GitHub Issues and the code remain the
source of truth for individual implementation details; update this document
whenever the branch, deployment, release gate, or working process changes.

## 1. Project identity

| Item | Value |
|---|---|
| Repository | <https://github.com/jerex763/unity> |
| Local workspace | `/Users/jeremy/cc/unity` |
| Active working branch | `codex/mvp-next` |
| Demo | <https://unity-fictional-demo.onrender.com> |
| Django Admin | <https://unity-fictional-demo.onrender.com/admin/> |
| Hosting | Render Free Docker web service |
| Database | Neon Free PostgreSQL |
| Backend | Django 5.2, Django REST Framework, PostgreSQL |
| Frontend | React, TypeScript, Vite, responsive PWA |
| CI | GitHub Actions |

Unity is an internal church people, event/check-in, and newcomer follow-up tool.
It may be productized later, but the current goal is a safe, small pilot—not a
complete church-management platform.

Permanent exclusions remain: facial recognition, sentiment surveillance,
ethnicity/race collection, and in-app payment processing. See
[`docs/roadmap.md`](docs/roadmap.md).

## 2. Current technical state

Verified on 2026-08-20:

- `codex/mvp-next` remote and deployed code HEAD:
  `e204ee1 Separate check-in access from directory writes`.
- The local branch contains one additional docs-only handoff commit that has not
  been pushed; no application code differs from the deployed remote branch.
- `main` remains protected at `a2ba850`; `codex/mvp-next` is 20 commits ahead.
- There is no authorization to merge or open a PR into `main`.
- GitHub CI for `e204ee1` passed:
  <https://github.com/jerex763/unity/actions/runs/32339216386>.
- Render health check returned `200 {"status": "ok"}`.
- The new authenticated check-in-person route is deployed; an unauthenticated
  request returns the expected `403`, confirming the new route is live.
- The only expected untracked path is `output/`. It belongs to the user and must
  remain untouched.

The Render service automatically deploys `codex/mvp-next` after linked GitHub
checks pass. The demo is temporary evaluation infrastructure, not production.
It may cold-start after inactivity.

## 3. Product state

### Implemented and usable with fictional data

- Django/Unity session login and active-church selection.
- Church tenancy and `ChurchMembership` roles: Admin, Pastor, Leader, Member.
- People directory, search/filter, profiles, preferred names, relationships,
  CSV import, lifecycle controls, audit events, and consent records.
- Event CRUD, duplication, public registration links, cancellation, registration
  roster, separate event-day check-in page, manual check-in, and walk-ins.
- First-visit follow-up creation on actual check-in rather than registration.
- Follow-up stages, assignment, due date, next action, interactions, outcomes,
  closure, worker dashboard, and stalled-action visibility.
- WhatsApp- and WeChat-first contact actions, with phone and email fallbacks.
- Responsive/modal UI fixes from the August fictional worker rehearsal.
- Render/Neon fictional-data demo and guarded fictional-data cleanup tooling.

### Latest completed implementation: Issue #109

Issue: <https://github.com/jerex763/unity/issues/109>

The code is implemented, reviewed, tested, pushed, and deployed at `e204ee1`.
GitHub still shows the Issue as **OPEN**; close it only after the recorded product
acceptance/update is complete.

Key behavior:

- `WRITE_PERSON_DIRECTORY`: Admin and Pastor only.
- `EVENT_CHECK_IN`: Admin, Pastor, and Leader.
- Leaders retain scoped directory reads and assigned follow-up work, but cannot
  create/edit profiles or relationships.
- Event check-in offers explicit **Existing person** and **New visitor** paths.
- Existing-person search is same-church, capped, and returns only minimal masked
  identity/contact hints. It excludes anonymized, deactivated, and inactive
  people.
- Existing-person check-in never mutates the selected profile.
- A registered or walk-in status is preserved; a waitlisted person becomes
  registered when actually checked in; a cancelled registration is revived as
  a walk-in and clears its stale cancellation token.
- A member who did not register can be selected on the check-in page and gets a
  walk-in registration plus manual check-in.
- New visitors still require at least one contact method. Exact normalized
  contact reuse is retained to reduce duplicates, but names are never used for
  automatic identity matching.
- Cross-church and lifecycle-inactive IDs are rejected. Contact matching locks
  candidates before lifecycle decisions to prevent a deactivation/check-in race.
- First-event follow-up creation remains visitor-only and check-in-triggered.

Verification evidence for #109:

- Backend: 272 passed, 4 PostgreSQL-only skips on the SQLite full run.
- PostgreSQL 16 lifecycle/check-in concurrency regression passed separately.
- Root-agent focused backend rerun: 60 passed.
- Frontend: Prettier and ESLint passed; 109 Vitest tests passed; production build
  passed.
- Playwright: 24/24 across 320, 375, 430, and desktop viewports.
- Independent final review: ACCEPT after two lifecycle/concurrency blockers were
  fixed.

### Important product decisions from the rehearsal

- International-student ministry is the likely first use case. WhatsApp and
  WeChat are primary; email must not be treated as the default follow-up channel.
- Transport requests and `Needs transport` were removed from event registration.
- Contact collection means “provide at least one method”; individual methods are
  optional. Avoid contradictory required/optional labels.
- Public registration collects identity/contact again. Identity resolution may
  use safe exact normalized contacts; it must never merge by name alone.
- Registration administration and event-day check-in are different jobs. The
  roster may show registrations, but rapid check-in belongs on the dedicated
  check-in page.
- Edit, duplicate, and follow-up update forms use clear modal/context behavior;
  do not reveal an editor far below the clicked item.
- Mobile layouts must not require horizontal page scrolling. Validate at 320,
  375, and 430 px as well as desktop.
- UI changes with meaningful workflow/design judgment should be shown for user
  approval before implementation. Small explicitly approved fixes can be made
  directly.

## 4. Authorization contract

The backend is authoritative; hiding frontend controls is not security. All
lookups are active-church scoped and cross-church object IDs should appear as
`404`.

| Capability/action | Admin | Pastor | Leader | Member |
|---|---:|---:|---:|---:|
| Read People directory | Church-wide | Church-wide | Scoped group people | Own linked Person |
| Create/edit Person and relationships | Yes | Yes | No | No |
| Event create/edit/duplicate | Yes | Yes | Yes | No |
| Event check-in, walk-in, check-in search | Yes | Yes | Yes | No |
| Read/manage follow-ups | Church-wide | Church-wide | Assigned to self | No |
| Consent read/write | Yes | Yes | No | No |
| CSV export | Yes | No | No | No |
| Deactivate Person | Yes | Yes | Scoped existing policy | No |
| Anonymize/hard-delete | Admin under lifecycle rules | No | No | No |
| Confidential care | Church-wide | Church-wide | No | No |

Read [`docs/permission-matrix.md`](docs/permission-matrix.md) and executable
permission tests before changing authorization. Changes involving tenancy,
person lifecycle, pastoral data, or role boundaries require a Sol-level design
or review task and explicit regression tests.

## 5. Current release gate and human work

The MVP code is substantial, but Unity is **not production-ready**. Issue #32,
the controlled pilot release gate, is still open.

Three human testers have been identified:

- one test Pastor;
- one test check-in worker;
- one test follow-up worker.

The Team Lead must provide each tester with a separate temporary account, only
fictional test records, and a role-specific step-by-step checklist. Disable or
remove temporary access and clean fictional test data after the authorized run.

Still required before claiming the pilot gate is complete:

1. Run a controlled end-to-end activity with the three workers on their phones.
2. Use fictional/minimum-necessary participant data unless a later privacy gate
   explicitly authorizes real data.
3. Capture workflow feedback without personal or pastoral content.
4. Recheck role boundaries and cross-church/confidential visibility.
5. Restore an encrypted backup into an isolated non-production database and
   verify aggregate counts and Django checks.
6. Complete [`docs/pilot-review-2026-07.md`](docs/pilot-review-2026-07.md).
7. Choose the next product work from observed evidence rather than assumptions.

When real worker participation is needed, tell the user exactly who is needed,
what each person tests, estimated time, account delivery method, fictional data
rules, and cleanup plan. Do not merely say “manual testing required.”

## 6. Open work and priority

GitHub open Issues verified on 2026-08-20:

### Immediate release work

- **#109** — implementation deployed; record acceptance and close/update the
  Issue when appropriate.
- **#32** — run the controlled human pilot and complete the release review.
- **#99** — configure and verify production-grade backups before re-enabling the
  daily schedule. Manual workflow remains the safer fallback until verified.

### Deliberately later

- **#16** QR check-in—do not promote before manual check-in succeeds in the
  controlled pilot.
- **#22–#25** Groups, group health, care kanban, and prayer quick-add—schedule
  only after pilot evidence. #24 is privacy-sensitive.

Do not start a “next issue” solely because the number is next. Re-evaluate value,
dependencies, privacy risk, and pilot evidence first.

## 7. Demo data and safety rules

- The Render/Neon environment is fictional-data-only.
- Historical test runs used RUN_ID-tagged fictional records and received
  separate user authorizations for creation and cleanup.
- Do not assume the current database is empty. Inspect counts/targets read-only
  before any future cleanup.
- A prior cleanup intentionally preserved the Django superuser while removing
  church/business data. Never change or disclose its credentials.
- Never paste Neon URLs, passwords, session cookies, CSRF tokens, private logs,
  or other secrets into chat or Git.
- Creating a test account, creating fictional test data, accepting a human test,
  cleaning data, pushing code, and merging to `main` are distinct approvals.
- Before destructive cleanup, identify exact RUN_ID/records, show the scope,
  obtain explicit authorization, and use guarded project commands/admin flows.
- Preserve auditability. Do not delete audit evidence unless the approved test
  cleanup procedure explicitly includes fictional audit rows.

See [`docs/person-data-lifecycle.md`](docs/person-data-lifecycle.md),
[`docs/demo-deployment.md`](docs/demo-deployment.md), and
[`docs/backup-restore-runbook.md`](docs/backup-restore-runbook.md).

## 8. Team Lead execution process

The user expects a Team Lead, not an order-taking code generator.

### Start of every new chat/work session

1. Read `AGENTS.md` and this document.
2. Confirm repository path, current branch, HEAD, remote divergence, and status.
3. Preserve `output/` and identify any unrelated user changes.
4. Check the relevant Issue and only the specialist docs needed for the task.
5. State the current outcome/next decision; do not replay historical narration.

### Product and issue intake

1. Restate the operational problem and the user roles involved.
2. Evaluate the proposal neutrally: workflow fit, MVP value, privacy, tenancy,
   accessibility, mobile behavior, data migration, and failure recovery.
3. Reject or reshape proposals that create ambiguity, duplicate concepts, unsafe
   identity matching, or disproportionate scope.
4. Define acceptance criteria and out-of-scope items before implementation.
5. For meaningful UI redesign, show the intended UI/flow for approval first.

### Multi-agent routing

Use subagents only when the current runtime permits it and the user/project
instructions call for delegation. Keep tasks bounded and avoid simultaneous
write-heavy agents in the shared worktree.

- **Luna:** documentation research, code mapping, mechanical edits, test
  additions, log summarization, and simple checks.
- **Terra:** normal feature implementation and medium-complexity changes.
- **Sol:** architecture, permissions/privacy, concurrency, migrations, complex
  debugging, and final independent review.

For business-code changes, prefer an implementation agent plus a different
independent reviewer. The Team Lead owns requirements, scope, evidence, Git,
deployment, and user communication. The implementer cannot be the sole reviewer.

### Implementation and validation

1. Inspect status/diff before assigning or editing.
2. Make the smallest defensible change and preserve unrelated work.
3. Add tests at the same layer as the risk:
   - backend service/API tests for business rules and RBAC;
   - PostgreSQL tests for row locking, constraints, and migration behavior;
   - frontend unit tests for state/render behavior;
   - Playwright for real responsive flows, focus, and overflow.
4. Run focused tests while iterating, then the proportional full quality gates.
5. Give the final diff to an independent reviewer, fix blockers, and re-review.
6. Do not call work complete because code compiles; require behavior evidence.

### Commit, push, deploy, and Issue handling

Each is a separate step:

1. Confirm intended files; never stage `output/` or unrelated changes.
2. Commit only after tests and independent review pass.
3. Push only with explicit user authorization.
4. `codex/mvp-next` deploys after GitHub checks pass. Monitor CI and verify
   `/api/health/` plus one feature-specific signal.
5. A health `200` alone proves availability, not that the new version is live.
6. Update/close the Issue only after its required automated and human acceptance
   evidence is recorded.
7. Do not merge or create a PR to `main` without fresh authorization.

## 9. Standard verification commands

Run from the repository root unless noted.

Backend:

```bash
cd backend
.venv/bin/black --check .
.venv/bin/ruff check .
.venv/bin/pytest -q
.venv/bin/python manage.py makemigrations --check --dry-run
```

Frontend:

```bash
cd frontend
npm run format:check
npm run lint
npm test -- --run
npm run build
npm run test:e2e
```

Repository and deployment:

```bash
git status --short
git diff --check
gh run list --repo jerex763/unity --branch codex/mvp-next --limit 5
curl -fsS https://unity-fictional-demo.onrender.com/api/health/
```

Do not blindly run destructive management commands or production-connected tests.
PostgreSQL concurrency/migration tests should use an isolated test database and
must verify teardown.

## 10. Documentation map

- Current handoff and workflow: this file.
- Delivery order and release gates: [`docs/delivery-plan.md`](docs/delivery-plan.md).
- Full vision and permanent exclusions: [`docs/roadmap.md`](docs/roadmap.md).
- Feature ledger: [`docs/features.md`](docs/features.md).
- Authorization contract: [`docs/permission-matrix.md`](docs/permission-matrix.md).
- Pilot checklist: [`docs/pilot-runbook.md`](docs/pilot-runbook.md).
- Pilot findings template: [`docs/pilot-review-2026-07.md`](docs/pilot-review-2026-07.md).
- Demo deployment: [`docs/demo-deployment.md`](docs/demo-deployment.md).
- Backup/restore: [`docs/backup-restore-runbook.md`](docs/backup-restore-runbook.md).
- Person lifecycle: [`docs/person-data-lifecycle.md`](docs/person-data-lifecycle.md).
- Public registration: [`docs/public-event-registration-pilot.md`](docs/public-event-registration-pilot.md).
- Contact/email decision: [`docs/outbound-email-pilot.md`](docs/outbound-email-pilot.md).
- Visual language: [`docs/design.md`](docs/design.md).

## 11. Handoff maintenance rule

Update this document in the same change whenever any of these changes:

- active branch or merge policy;
- deployed commit or hosting topology;
- pilot/release gate status;
- role/capability rules;
- fictional/real-data authorization boundary;
- prioritized open Issues;
- test/deployment workflow;
- subagent routing policy.

Keep it concise enough to read at session start, but complete enough that a new
Team Lead does not need prior chat history.
