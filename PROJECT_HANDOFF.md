# Unity project handoff and operating guide

Last verified: **2026-09-07 (Australia/Sydney)**

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

Verified on 2026-09-07:

- Latest application delivery is now `09c2a41`, pushed with explicit user
  continuation authorization. CI `34125318906` passed all four jobs; Render
  `dep-dafbdn942hec73d2vtug` / GitHub deployment `6309329134` succeeded at
  `2026-09-07T13:07:51Z`. A documentation-only follow-up records this evidence.
- Live health is 200/ok, home and Events SPA routes return 200, unknown API 404.
  Anonymous public-link recovery is 403 with no-store. Live
  `index-BwfoW3yg.js` / `index-De9yAWE-.css` match tested local build bytes,
  including the new result region and legacy-link wording.
- After separate explicit user authorization, live fictional event #9 was created
  and its new public link copied successfully, then copied again after a full
  Events reload with exact URL equality. Its public registration form displayed
  the correct event. No registration was submitted; existing event #8 and its
  link were not modified. Current key encryption/recovery is verified for this
  new link; key custody and rotation remain unverified. The test event is retained
  pending separate cleanup authorization. See
  [`docs/public-link-live-verification-2026-09-07.md`](docs/public-link-live-verification-2026-09-07.md).
  No encryption key value was read or public URL recorded in evidence. Production
  backup cron remains paused; #99's prerequisite repair is deployed, not a
  completed operational backup setup.

- Previous application delivery was `47fcdcc` on `codex/mvp-next`, pushed and
  deployed with explicit user authorization. A documentation-only follow-up
  records this deployment; use Git for its exact HEAD. `main` remains `a2ba850`.
  No PR or merge to main was requested or performed.
- CI run `34114621918` passed Frontend, Backend, Deployment image and Backup
  restore for `47fcdcc`.
- Render deployment `dep-daf9kr95efls73aja2o0` (GitHub deployment `6307308121`)
  reported success at `2026-09-07T11:06:34Z` for `47fcdcc`.
- Live verification returned health `200 {"status":"ok"}`; `/`, `/people/123`
  and `/follow-ups?task=71` serve the SPA, admin CSS returns 200, and an unknown
  API endpoint returns 404. These route probes do not assert authenticated
  access to a real person or task.
- Live `index-B-FR7G0t.js` and `index-C-EEBaEX.css` exactly match the tested local
  build bytes. The JavaScript contains the new Back controls, contact disclosure
  and mobile-detail signals. No live business data was written during checks.
- Historical Batch 1 Render deployment `dep-da8ikdm417fc73ddk0vg` succeeded. Health returned
  `200 {"status":"ok"}` and the demo serves `index-Dzur2OWn.js` plus
  `index-Bl8U4DgH.css`; the deployed JavaScript contains the new profile,
  Engagement and save-confirmation signals.
- `output/` is untracked user-owned output and must remain untouched. The other
  current untracked paths—`.agents/`, `skills-lock.json`, and
  `docs/ui-mockups/`—are intentional local design-skill and People/Profile mock
  artifacts. Review their exact contents before any future commit; do not stage
  them merely because they are present.
- Project-scoped skill `.codex/skills/redesign-existing-projects/SKILL.md` is
  installed for the next UI audit. Use its scan/diagnose/focused-fix workflow
  selectively; Unity is an operational mobile web app, so marketing-page motion,
  decorative imagery and framework/library changes are out of scope unless the
  user separately approves them.
- The resulting read-only audit is recorded in
  [`docs/ui-audit-2026-08-28.md`](docs/ui-audit-2026-08-28.md). It recommends a
  three-batch, dependency-free redesign beginning with mobile church context,
  explicit task actions and visible post-save outcomes. The user approved Batch
  1; it is reviewed, tested, pushed and deployed under Issue #110.

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

### Latest deployed implementation: pre-pilot workflow polish

The user approved three small workflow fixes after reviewing the prepared phone
test screens. They are implemented, pushed, and deployed at `3e7faf7`:

- Event-day check-in defaults to **To check in**, adds **All**, retains
  **Checked in** and **Walk-ins**, and makes a typed attendee search global
  across all non-cancelled registrations. Each result now states both its
  registration source/status and current check-in state.
- The organizer event card shows the combined active registration and waitlist
  count on the control that opens the registration roster, making public-link
  submissions discoverable without changing the underlying data model.
- Follow-up **Update** opens a real accessible modal, consistent with event
  editing. It traps focus, closes with Escape, restores focus to the trigger,
  and uses the existing full-screen mobile treatment.

This is frontend-only polish: there are no backend, permission, tenancy, data,
or migration changes. Verification passed: Prettier, ESLint, all 109 Vitest
tests, the production build, and all 24 Playwright checks across 320, 375, 430,
and desktop viewports. GitHub CI run `32385692091` passed all frontend, backend,
deployment-image, and backup-restore jobs. Render returned a healthy response
and served the new `index-DUmJuRx3.js` bundle containing the new check-in and
registration controls.

### Latest deployed implementation: Issue #110 Batch 1

Issue: <https://github.com/jerex763/unity/issues/110>

The first evidence-backed mobile UI batch is deployed:

- every mobile route shows active church and role in the sticky shell;
- dashboard follow-up actions are 44px button targets and due dates are more
  prominent with consistent `DD/MM/YYYY` summaries;
- a person's full summary row opens the profile, `Edit person` is in the profile
  header, and read-only contact values no longer look like form inputs;
- profile and follow-up saves show confirmation, return the viewport to the
  updated summary, and move keyboard focus to the relevant heading;
- Follow-up Update initially focuses its heading instead of Stage, explains
  Engagement and Outcome, and displays a saved Outcome in task detail.

This is a frontend-only change at `2dc7d20` with no API, permission, tenancy,
token, data, or migration changes. Prettier, ESLint, all 109 Vitest tests, the
production build, and all 35 Playwright checks across 320, 375, 390, 430 and
desktop passed locally and in CI. The browser suite includes visible
long-context and edit-entry/post-save sticky-header boundary assertions.
Independent final review returned **ACCEPT** after three passes and two rounds
of viewport-boundary fixes. CI run `33147843372` and Render deployment
`dep-da8ikdm417fc73ddk0vg` passed; feature-specific bundle signals were verified
on the live demo.

### Current authorized frontend delivery — 2026-09-07

The user chose reliability → task reorganization → visual convergence and
explicitly delegated scoped product/design decisions to the Team Lead because
new human testing is not practical now. The scoped implementation is complete
and independently reviewed locally, documented in
[`docs/frontend-delivery-2026-09-07.md`](docs/frontend-delivery-2026-09-07.md).
The local task-flow mock precedes implementation. Keep the current desktop
sidebar, API/permissions and whole-profile editor; directory contact disclosure,
phone task/roster navigation and failure/pending recovery are the selected scope.
This delegation does not grant push/deploy, account/data or cleanup authorization.
Automated verification must not be relabelled as human acceptance.

Delivered: recoverable Profile/public-link loads; stale request isolation;
per-record check-in pending guards and event-route state reset; session-memory
Directory filters/search/return focus; collapsed contact disclosure with readable
values; exact task deep links and phone detail/Back; focused phone event rosters;
operational heading/filter spacing. No backend or permission contract changed.

Final local checks: Prettier, ESLint, 121 Vitest tests, production build, and
65/65 Playwright tests across 320/375/390/430/desktop passed. Independent review
returned **ACCEPT**, including re-review of event-route races and sticky-header
Back visibility. Actual fictional screenshots/layout evidence are in
`docs/ui-delivery-2026-09-07/`. The delivery was committed at `47fcdcc`, then explicitly authorized for push and
deployment. It is now live; CI, Render and feature-specific verification evidence
are recorded in section 2. `output/` remains untouched. No new human acceptance,
account/data changes or cleanup is claimed; #32 remains open. Next priority is
remaining pilot/release evidence, not another speculative redesign. Human testing
is deferred at the user's request.

### Current read-only reassessment — 2026-09-07

The user requested a fresh senior frontend review that distinguishes facts,
assumptions and preferences. See
[`docs/ui-audit-2026-09-07.md`](docs/ui-audit-2026-09-07.md).
Local mocked-API Chromium inspection reproduced a stuck Profile loading state
on a 503 response, clipped contact values, off-screen selected follow-up detail,
loss of Directory search on browser Back, repeated check-in requests while
pending, and misleading public-registration failure wording. These are audit
findings from the original audit, not claims of production incidents. The
confirmed defects are now repaired locally in the delivery immediately above.

The new recommendation is reliability and task-navigation repairs before
committing to the People/Profile editing model. The existing mock is a candidate,
not an approved specification: removing all directory contact actions and
section-level editing remain hypotheses. Its desktop bottom navigation should
not replace the existing sidebar without evidence. The later Team Lead
delegation authorized the narrower task-flow delivery above; it did not approve
the whole earlier People/Profile proposal.

### Public-link recovery — deployed

The user approved design, implementation, local commit and then continuation to
push/deploy. Commit `09c2a41` is now deployed; CI/Render/live-version evidence is
recorded in section 2. Full design and validation:
[`docs/public-link-recovery-design.md`](docs/public-link-recovery-design.md).

Encrypted storage, explicit same-church Admin/Pastor/Leader recovery permission,
fresh Copy/Show with pending/retry/manual-copy behavior, no-store responses and
identifier-only audit are implemented. Legacy links remain valid without
automatic rotation; their missing ciphertext cannot be reconstructed.

Verification: full PostgreSQL 16 suite 305 passed, independent PostgreSQL 32 passed,
frontend 130 unit tests, full Playwright 75 passed, build/static checks and independent
review ACCEPT. Screenshot/layout evidence: `docs/public-link-recovery-evidence/`.

The user reports PUBLIC_LINK_ENCRYPTION_KEYS configured and backed up; its actual
format/decryptability was not read or validated in live business operations.
Missing/invalid keys block new creation/replacement/recovery but do not invalidate
existing public URLs. No production key belongs in chat/Git/logs. Old keys needed
for retained backups must remain in separately protected recovery custody.

### Current design proposal: People/Profile follow-up

The next People/Profile change is design-only and has not been implemented in
the application. Review artifacts are stored locally under
[`docs/ui-mockups/`](docs/ui-mockups/), with the rationale in
[`people-profile-redesign-2026-08-29.md`](docs/ui-mockups/people-profile-redesign-2026-08-29.md).
The proposal makes the People directory selection-focused, removes duplicate
contact information from Profile Overview, and uses section-level in-place edit
actions. After save, the intended behavior is to leave edit mode, show a clear
confirmation, and return focus/viewport to the section just edited—not
unconditionally to the top of the Profile. Existing previews cover four states
at 390 × 844 only. The local
[`2026-09-07 review supplement`](docs/ui-mockups/people-profile-review-2026-09-07.html)
adds selectable 320/375/390/430/1440 widths and eight static states: directory,
Overview, Details edit, Contact edit, saving, save failure, saved Details and
read-only profile. All 40 state/width combinations passed local static-layout
checks; this does not replace application interaction tests. Review notes are in
[`the supplement record`](docs/ui-mockups/people-profile-review-2026-09-07.md).
Obtain explicit visual approval before production changes. No such approval was found in the current
handoff or Issue #110. Its existing comment already records Batch 1 technical
delivery; post-deployment human acceptance remains distinct.

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
  375, 390, and 430 px as well as desktop.
- UI changes with meaningful workflow/design judgment should be shown for user
  approval before implementation. Small explicitly approved fixes can be made
  directly.
- The current real-event Google Form is workflow evidence, not authorization to
  import its responses into the fictional demo. Unity should keep affirmative
  registration plus separate cancellation rather than copy ambiguous
  attending/cannot-attend/maybe checkboxes.
- WhatsApp channel availability or preference is not consent to add someone to a
  WhatsApp group. Any future group-addition workflow requires separate specific
  consent and disclosure of member number visibility.
- Student/worker, course and industry questions remain pilot hypotheses. Do not
  build a general form builder or write event answers into permanent profiles
  without repeated operational evidence. Do not add religious background to
  public event registration by default.

See
[`docs/current-event-registration-review-2026-08.md`](docs/current-event-registration-review-2026-08.md).

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

Three human testers completed the controlled phone session:

- one test Pastor;
- one test check-in worker;
- one test follow-up worker.

The three role-specific 10–15 minute phone checklists are recorded in
[`docs/pilot-runbook.md`](docs/pilot-runbook.md), with a directly shareable
bilingual text version in
[`docs/pilot-phone-test-steps-2026-08-28.txt`](docs/pilot-phone-test-steps-2026-08-28.txt).
All three workers reported independent completion with fictional data. Their
de-identified usability findings and the Team Lead's isolated supplemental
public-registration review are recorded in
[`docs/pilot-review-2026-07.md`](docs/pilot-review-2026-07.md). The live public
link was not rotated because doing so would invalidate its existing URL.

Still required before claiming the pilot gate is complete:

1. Record device/browser and approximate-duration details if the workers can
   provide them without including personal or pastoral content.
2. Recheck role boundaries and cross-church/confidential visibility against the
   completed session evidence.
3. Disable/remove temporary test access and clean fictional session data only
   after separate authorization.
4. Restore an encrypted backup into an isolated non-production database and
   verify aggregate counts and Django checks.
5. Complete the remaining controlled-activity fields in
   [`docs/pilot-review-2026-07.md`](docs/pilot-review-2026-07.md).
6. Record Batch 1 acceptance on #110 and decide whether the People/Profile visual
   proposal is approved before implementing that follow-up scope.

The confirmed reliability/navigation defects have been repaired, validated and deployed
under the explicitly authorized scope above. The larger People/Profile editing proposal remains
a separate future decision; automated evidence does not close the pilot gate. Account
deactivation, fictional-data cleanup, public-link rotation and backup restore
remain separate operational actions requiring their documented authorization.
The completed check-in worker run supplies the remaining product-acceptance
evidence for #109; record that evidence before closing the Issue. Data/account
cleanup remains a separate post-session authorization.

The `20260814-0005` demo baseline was restored and verified on 2026-08-25 after
separately authorized cleanup. The event-day **To check in** view contains the
prepared registered visitor and follow-up worker, both not checked in; the
follow-up queue is empty; the People directory contains only the registered
visitor and three linked worker people (four total). The three temporary worker
accounts and their role/membership links remain active. Existing audit evidence
was preserved. Treat any changes made during the phone session as test output;
do not reset or clean them without a new cleanup authorization.

When real worker participation is needed, tell the user exactly who is needed,
what each person tests, estimated time, account delivery method, fictional data
rules, and cleanup plan. Do not merely say “manual testing required.”

## 6. Open work and priority

GitHub open Issues verified on 2026-09-07:

### Immediate release work

**2026-09-08 no-new-paid-services decision:** the user has no AWS setup and
explicitly deferred paid backup infrastructure. Pause #99 cloud setup; keep the
schedule disabled. Do not ask for AWS signup as the immediate next step. A local
encrypted backup/isolated restore is an optional later drill, not an existing
backup and not authorized by this documentation reconciliation. The demo remains
fictional-only; real participant data stays in the existing Google workflow.
Reliable recovery remains a gate before real-data adoption.

Current issue evidence was reconciled in
[`docs/pilot-status-reconciliation-2026-09-08.md`](docs/pilot-status-reconciliation-2026-09-08.md).
#109 needs evidence publication rather than reimplementation; #110 must distinguish
delivered task flows from deferred design ideas; #32 remains open with real-activity,
session audit and selected-backup restore evidence outstanding. GitHub issues
were read only and remain open. Do not repeat the completed worker session merely
to fill stale issue text.

Read-only backup setup audit on 2026-09-08 confirmed the GitHub
`production-backup` environment exists, with empty protection rules and no
deployment branch policy. After the user logged in, authenticated GitHub settings
confirmed both environment secrets and repository Actions secrets are empty.
All seven required backup secrets are therefore absent from those scopes; CLI
metadata still returns 403. Storage configuration and key custody remain unknown.
No workflow was dispatched.
The S3 lifecycle template expires current objects after 30 days but lacks
noncurrent-version expiry despite the runbook requiring versioning; resolve this
retention gap before any future schedule enablement. Cloud setup is now deferred
under the no-new-paid-services decision above.

The 2026-09-07 read-only release-gap check is recorded in
[`docs/release-gap-review-2026-09-07.md`](docs/release-gap-review-2026-09-07.md).
The reviewed baseline is `327d3d5`; CI `34114978337` and GitHub deployment `6307378878`
succeeded. All four issues below remain open. #109 chiefly needs evidence
reconciliation; #110 does not yet record the later deployed task-flow batch.
#32 already has worker feedback in the repository, so do not ask for a repeat
session merely because GitHub's preparation comment is stale.

**#99 prerequisite repair is now deployed at `09c2a41`:** pin the backup runner
at ubuntu-24.04, verify its AWS CLI v2, install only age/postgresql-client, and
preflight all seven settings before tools or database access. Nine offline
regression tests pass and the main agent independently reviewed the implementation.
CI now includes these tests; the production cron remains paused. These changes
passed CI `34125318906`; the production backup workflow itself was not run. Next operational
step remains verifying configured infrastructure and a specifically authorized
backup/restore drill, not automatically enabling the schedule. Latest backup run `29694284982` failed installation
and alerting, with no newer run found. Authenticated browser review subsequently
confirmed empty environment and repository secret scopes. CI's temporary
probe restore does not prove an operational backup is available. Infrastructure
setup, actual backup/restore and alert delivery remain separately scoped work.

- **Local 2026-09-07 frontend delivery** — scoped reliability, task navigation
  and visual convergence are implemented, tested and independently accepted in
  deployed commit `47fcdcc`; CI and feature-specific live verification passed.
  No issue update or new human acceptance is claimed. The larger People/Profile
  editing proposal remains separate.

- **#109** — implementation deployed; record acceptance and close/update the
  Issue when appropriate.
- **#110** — Batch 1 is deployed; record its acceptance and keep later
  People/Profile implementation behind the visual-approval gate.
- **#32** — reconcile the completed fictional worker session and remaining
  permission/restore/release evidence; new human testing is currently deferred.
- **#99** — cloud configuration deferred for cost; schedule remains disabled.
  Do not dispatch the unconfigured manual workflow. Revisit recovery before
  real-data use; a separately scoped local drill adds no cloud-service charge.

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
5. For meaningful UI redesign, create a reviewable visual mock before editing
   code. Use Figma when available or a local equivalent, show the actual target
   mobile/desktop widths and the primary interaction states, and obtain explicit
   user approval. A text-only description is not sufficient. Only a truly
   granular mechanical style fix may skip this gate, with the reason stated
   before implementation.

### Multi-agent routing

Use subagents only when the current runtime permits it and the user/project
instructions call for delegation. Keep tasks bounded and avoid simultaneous
write-heavy agents in the shared worktree.

- **Spark (optional fast lane):** use `gpt-5.3-codex-spark` only when the
  runtime explicitly offers it. It is for near-instant execution of a fully
  specified, low-risk, easily reversible task with cheap local verification,
  such as one granular UI adjustment, a mechanical edit, or a straightforward
  regression test. Do not use it for ambiguous requirements, product or
  architecture choices, API/data/permission contracts, cross-module changes,
  unknown-cause bugs, security, migrations, concurrency, live data, deployment,
  destructive work, or final review. Never claim a Spark handoff if the runtime
  could not select that model.
- **Luna:** documentation research, code mapping, mechanical edits, test
  additions, log summarization, and simple checks.
- **Terra:** normal feature implementation and medium-complexity changes.
- **Sol:** architecture, permissions/privacy, concurrency, migrations, complex
  debugging, and final independent review.

Do not create a Spark subagent solely because a task is small; for a five-minute
change, delegation overhead may exceed the work. When delegation is worthwhile,
the main agent defines acceptance criteria first. Only one agent may write to an
overlapping file/scope at a time; independent writers require isolated scopes or
worktrees. The main agent inspects the diff, targeted verification, and residual
risk before delivery.

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
- Shareable phone-test steps:
  [`docs/pilot-phone-test-steps-2026-08-28.txt`](docs/pilot-phone-test-steps-2026-08-28.txt).
- Pilot findings template: [`docs/pilot-review-2026-07.md`](docs/pilot-review-2026-07.md).
- Demo deployment: [`docs/demo-deployment.md`](docs/demo-deployment.md).
- Backup/restore: [`docs/backup-restore-runbook.md`](docs/backup-restore-runbook.md).
- Person lifecycle: [`docs/person-data-lifecycle.md`](docs/person-data-lifecycle.md).
- Public registration: [`docs/public-event-registration-pilot.md`](docs/public-event-registration-pilot.md).
- Current real-event form comparison:
  [`docs/current-event-registration-review-2026-08.md`](docs/current-event-registration-review-2026-08.md).
- Contact/email decision: [`docs/outbound-email-pilot.md`](docs/outbound-email-pilot.md).
- Visual language: [`docs/design.md`](docs/design.md).
- Latest read-only UI audit:
  [`docs/ui-audit-2026-09-07.md`](docs/ui-audit-2026-09-07.md).
- Earlier audit and Batch 1 rationale:
  [`docs/ui-audit-2026-08-28.md`](docs/ui-audit-2026-08-28.md).
- Pending People/Profile visual proposal:
  [`docs/ui-mockups/people-profile-redesign-2026-08-29.md`](docs/ui-mockups/people-profile-redesign-2026-08-29.md).

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

At the end of material project work, reconcile the resulting Git/GitHub,
CI/deployment, acceptance, product decision, risk, blocker, and next-priority
state here. Do not update it merely to change a timestamp when nothing durable
changed.

Keep it concise enough to read at session start, but complete enough that a new
Team Lead does not need prior chat history.
