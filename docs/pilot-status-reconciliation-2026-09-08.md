# Pilot status reconciliation — 2026-09-08

Read-only GitHub review of #109, #110 and #32, compared with repository delivery
and worker evidence. All three issues remain OPEN; no comments or edits were
published. Local HEAD is `5c665d1` on `codex/mvp-next`. No code, deployment,
account, data or infrastructure operation was performed.

## Evidence and recommended issue treatment

| Issue | Evidence available | Recommended treatment |
|---|---|---|
| #109 — check-in access and existing-person walk-ins | Handoff records deployed permission split; issue defines role, cross-church, registration and profile-preservation acceptance. Pilot review records independent check-in-worker completion. | Prepare evidence publication, not a fresh implementation. Generic worker completion does not establish that every listed edge case was manually exercised; cite executable tests separately before closure. |
| #110 — mobile workflows | Existing GitHub comment records Batch 1 at `2dc7d20`, 109 unit / 35 browser checks and independent ACCEPT. `docs/frontend-delivery-2026-09-07.md` records later deployed `47fcdcc`, 121 unit / 65 browser checks, focused phone task/roster flows and recovery. | Update the delivered-versus-deferred scope when publication is requested. Keep parent open for unresolved scope decisions; do not relabel automated checks as human acceptance. |
| #32 — controlled pilot | Three actual workers' fictional-data feedback and worked/failed/next recommendations exist in `docs/pilot-review-2026-07.md`. CI probe restore and permission tests are recorded. | Worker feedback is no longer missing. Real-activity evidence, session-specific permission/audit review and selected-backup restore remain outstanding; do not close or authorize real data implicitly. |

## Important boundaries

The public-link recovery change (`09c2a41`) adds backend/schema behavior and must
not be presented as satisfying #110's frontend-only/no-migration scope. Its own
delivery and live verification records cover that feature. Live test event #9
remains retained with zero submitted registrations from that verification; no
cleanup is authorized here.

Historical #32 comments describe earlier permission findings; those comments are
not proof that a defect remains in today's code. Conversely, passing generic
permission tests is not a session-specific audit. Resolve each claim against the
current implementation before declaring it closed.

## Current decision and next work

The user does not want new paid services. Defer AWS/cloud backup setup and keep
the production backup schedule paused. Do not dispatch the manual workflow while
its seven required secrets are absent. No AWS signup is needed now.

Continue fictional-only evaluation. Existing real participant information stays
in the Google workflow; no migration is part of this work. A local encrypted
backup and isolated restore can be scoped later without a new cloud-service fee,
but it is not yet executed and would not replace off-device recovery protection.

Next engineering evidence task, if continuing: map #109's acceptance criteria to
current test cases and examine outstanding role-boundary findings locally. Use
isolated fictional fixtures if additional execution is needed. Prioritize proven
permission or workflow failures over new modules, visual redesign or typo-tolerant
search. No new human session is requested merely to repair documentation drift.
