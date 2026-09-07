# Pilot review — August 2026

Issue: [#32](https://github.com/jerex763/unity/issues/32)

## Current status

The automated fictional rehearsal and the controlled phone session with three
actual workers are complete using fictional participant data. All three workers
reported that they could complete their assigned task independently. The session
also exposed substantial mobile usability friction, recorded below. The
Render/Neon demo is not authorized for real participant data, and this review
must not be marked complete until the remaining gates have recorded evidence.

| Gate | Evidence | Status |
|---|---|---|
| Signup → manual check-in → walk-in → follow-up → outcome | `backend/tests/test_pilot_flow.py` | Passed with fictional data |
| Cross-church and confidential access | `backend/tests/test_permission_matrix.py` plus role-specific API tests | Passed with fictional data |
| Encrypted backup restore | Pull-request **Backup restore** check using PostgreSQL 16 and fictional probes | Passed in CI |
| Mobile worker use | Pastor, check-in worker and follow-up worker on their own phones | Passed with significant usability findings on 2026-08-28 |
| Controlled worker session | All three workers reported independent completion of their fictional workflow | Passed on 2026-08-28 |
| Isolated restore drill | Restore a selected encrypted backup outside production and verify aggregates | Pending |
| AI release safety | No AI feature is in the pilot scope | Passed |

## Controlled activity record

- Date and activity:
- Pilot owner:
- Workers and roles (do not list participant details):
- Software version / commit:
- Backup timestamp restored:
- Restore duration and outcome:
- Permission or audit findings:
- Fictional dataset RUN_ID (no credentials):
- Account cleanup outcome:

The blank activity fields are retained as unknown; they must not be filled with
the September agent-run public-link test or treated as a real-attendee activity.
See the 2026-09-08 reconciliation below for the current delivery state.

## Worker feedback

Record themes without personal or pastoral content.

| Worker role | What worked | Friction or failure | Suggested change |
|---|---|---|---|
| Pastor | Independently completed registration review, person update and follow-up work | Active church hidden on phone; registration roster opens far below the event and uses little of the screen; only the person's name reveals the profile; edit is below the fold; contact values look editable but are not; save leaves the viewport at the bottom; mobile follow-up selection reveals detail below the queue; due-date presentation is weak | Keep church context visible; use a full-screen mobile roster/detail flow; make person-card and edit actions explicit; restore focus/scroll after save; format dates as `DD/MM/YYYY` in summaries |
| Check-in worker | Independently completed event-day check-in | Active church hidden; attendee and existing-person search felt exact because it does not tolerate misspelling and the two searches cover different populations | Keep church context visible; explain search scope; show suggestions after two characters; support safer token/preferred-name matching before considering an all-name browser |
| Follow-up worker | Independently completed assigned follow-up | Active church hidden; dashboard actions are small underlined links; due date lacks emphasis; Stage selector opens immediately on mobile; WhatsApp action was absent for the prepared record; Engagement and Outcome are unclear; saved Outcome is not visible in the task summary; email layout is cramped | Use large touch targets and prominent due state; focus the dialog heading instead of Stage; verify fictional contact flags; explain or simplify Engagement; display saved Outcome; stack mobile contact actions |

The session did not report a permission failure. Device/browser and elapsed-time
details were not supplied and remain blank rather than inferred.

## Registration-form hypotheses

Use the comparison in `docs/current-event-registration-review-2026-08.md`.
Record only whether a field caused a concrete worker action; do not record an
attendee's answer.

| Hypothesis | Observed worker action | Repeated across roles/events? | Decision |
|---|---|---|---|
| Separate WhatsApp group consent is needed | A specific opt-in could trigger a named administrator to send a group invitation; having a WhatsApp-capable phone is not consent | Not tested across events | Define purpose, owner, visibility and withdrawal before collecting |
| Student/worker context changes event work | No current public field or named routing/action consumes the answer | Not observed | Defer |
| Course or industry changes event work | No current mentor/group-matching owner or workflow consumes the answer | Not observed | Defer |
| Future-event subscription has a named owner/workflow | No auditable subscription, channel owner or withdrawal workflow exists | Not observed | Do not collect until the workflow exists |
| Religious background is necessary at registration | | | Do not collect by default |

## Agent-run supplemental review — 2026-08-28

At the pilot owner's request, the Team Lead independently completed the omitted
public-registration and field-actionability review. This is product-analysis
evidence, not a substitute for human worker evidence.

- Live demo health returned `200 {"status": "ok"}` after a Render cold start.
- A read-only mobile review confirmed the fictional event has an active public
  registration link, but the UI cannot reveal an existing raw URL. Only its
  active state is retained because the server stores a token digest. Rotating
  the link would invalidate the old URL, so the live link was not rotated.
- Isolated backend verification passed: `23 passed, 1 skipped` for
  `test_public_event_registration.py` and `test_pilot_flow.py`.
- Focused frontend verification passed: all 18 tests in `src/App.test.tsx`.
- The current public form does not collect student/worker status, study area,
  industry or future-event subscription. Those answers therefore cannot be
  observed in the current workflow.

An optional field is actionable only when an answer changes a named operational
decision: routing, assignment, deadline, event preparation, or a separately
consented communication. On present evidence, student/worker, study-area and
industry fields should remain deferred. A separate WhatsApp-group opt-in is the
only plausible near-term candidate, and only after its owner, wording, member
visibility, withdrawal path and retention are defined. Future-event contact
requires its own auditable subscription rather than a registration note.

## What worked

- All three workers reported independent completion of their assigned fictional
  workflow.
- Public registration, check-in and recorded follow-up outcome remain covered by
  passing isolated integration tests.

## What failed

- Mobile context, navigation, touch targets and post-save feedback did not meet
  the usability bar even though the tasks were completable.
- An already-active public registration URL cannot be copied or recovered from
  the UI; only a destructive replacement can reveal a new URL.
- The registration-field hypotheses were included only as a debrief question,
  not as an executable phone-test step.

## Recommendation

Do not add the proposed registration fields yet. The next product batch should
address the repeated mobile context and navigation defects, public-link
discoverability/recovery wording, and visible post-save feedback before adding
new modules. Keep QR check-in and Groups & Care in the later backlog. Any AI
proposal requires a separate evaluation set, human-review workflow, permission
analysis, and safe fallback.

Issue #110 now tracks that UI work. Its approved Batch 1 is reviewed, tested and
deployed at `2dc7d20`; it covers mobile church/role context, dashboard touch
targets, person-row and profile-edit discoverability, post-save feedback/focus,
Follow-up dialog entry focus, saved Outcome visibility and `DD/MM/YYYY` display
dates. These were the remaining items at the time of that review; the subsequent
delivery update below supersedes their status.

## Delivery and release reconciliation — 2026-09-08

- `47fcdcc` subsequently delivered focused phone roster/follow-up views, explicit
  return navigation, directory context preservation and failure/pending recovery.
  Recorded validation is 121 unit tests, 65 browser checks and independent ACCEPT;
  this is automated evidence, not another worker session.
- `09c2a41` delivered encrypted recovery for newly created public links. The
  separately authorized live event #9 check on 2026-09-07 verified identical
  copied URLs after reload and a correctly displayed registration form. No
  registration was submitted or existing pilot link replaced. Older digest-only
  links remain unrecoverable; the historical finding above remains valid for them.
- Search typo tolerance and wider People/Profile redesign are not established as
  delivered by these records. Keep them deferred pending specific evidence/value.
- The user deferred paid cloud backup setup. CI's fictional probe restore remains
  valid but does not satisfy the selected-demo-backup restore gate. No local
  operational restore is claimed.
- #32 remains open. Three-worker feedback exists, while device/browser/duration,
  activity-specific audit, selected-backup restore and cleanup remain incomplete.
  A real-attendee activity is neither authorized nor completed in this demo.

Detailed issue mapping: `docs/pilot-status-reconciliation-2026-09-08.md`.
