# Audit coverage review — 2026-09-08

Code baseline: `2f3035a`. Read-only source review and isolated tests; no live
audit rows, credentials or participant records were read or exported.

## Verified coverage

`audit/signals.py` records Person changes and membership role/access changes.
Explicit callers cover login results, consent, exports, confidential-care admin
views, public-link create/recover/revoke and public registration/cancellation.
`audit/services.py` limits metadata keys and selected reason codes; application
ORM and admin guards prevent ordinary audit edits/deletes. These are application
protections, not a claim of database-administrator-proof immutability.

Fresh isolated run with `TEST_DATABASE_URL` unset and
`DJANGO_SETTINGS_MODULE=config.settings.test`:

```text
test_audit.py
test_consent.py
test_interaction_api.py
test_public_link_recovery.py
42 passed, 4 skipped, 75 warnings
```

The four PostgreSQL-only locking cases were skipped under in-memory SQLite.
No new concurrency or live-session acceptance is claimed.

## Confirmed traceability gap

`EventRegistration` stores `checked_in_at` and `checkin_method`, but no check-in
actor. `set_manual_check_in` updates or clears attendance state without emitting
an audit event. The audit action enum and signal receivers do not supply a
registration check-in/correction history. Current registration state therefore
cannot reliably identify which worker checked someone in or reversed attendance.
This is not evidence of unauthorized access; it limits retrospective activity
review and correction accountability. Existing #109 functional/permission
acceptance is unaffected; #32 must not be marked fully audited on that basis.

## Recommended bounded follow-up (not implemented)

Add minimal audit events for actual attendance transitions across both manual
check-in and walk-in paths: actor, church, registration identifier, request ID,
timestamp and action (checked in / check-in reversed). Keep names, contact values,
notes and public tokens out of metadata. Repeated idempotent requests should not
create duplicate transitions; failures and denied requests must not create success
events. Audit creation should be atomic with attendance updates.

Before implementation, settle the event vocabulary, treatment of actor-less
internal operations and retention under the existing audit policy. Verify role
and tenant scope, ordinary attendance, existing/new walk-ins, reversal, retries
and transaction rollback. This is a privacy/audit-contract change requiring its
own scoped decision and independent review, not a cosmetic fix.

No new GitHub issue was created and no code or audit schema was changed. Paid
backup setup remains deferred. This review does not replace a selected live
activity's audit review or the outstanding recovery drill.

## Subsequent authorized implementation

The user approved proceeding. The local implementation adds `event.checked_in`
and `event.check_in_reversed` actions to the shared `set_manual_check_in` service.
Both manual attendance and existing/new walk-ins already use that service. Only
a change in the presence of `checked_in_at` emits an event, after the registration
row lock and inside the same transaction as attendance/follow-up writes. Audit
failure rolls back the operation; retries without a transition emit no event.

The existing request middleware supplies actor and request ID. Actor-less internal
calls retain a null actor and generated request ID, rather than inventing a user.
Metadata is empty; the target is the registration ID with church scope. Existing
audit access/retention rules are unchanged. No historical attribution is backfilled.
Migration `audit.0006` updates action choices; no participant fields or API response
changes are added. This is not auditing arbitrary direct database/admin edits.

Local verification: full PostgreSQL 16 suite **314 passed**; after adding one more
concurrent-request regression, the targeted attendance audit suite **10 passed**.
Migration apply, no-pending-migration check, Black and Ruff passed. The concurrent
test confirms two simultaneous check-in calls create one transition event.
Tests cover both walk-in paths, retries, reversal, denied/cross-church requests,
audit-failure rollback (including new Person/follow-up creation), request attribution
and no personal metadata. Independent Sol review returned ACCEPT with no blockers;
its isolated SQLite run passed 9 tests and skipped the PostgreSQL-only case.
The temporary PostgreSQL instance was stopped and removed after verifying its PID.
The user subsequently authorized commit, push and deployment. Live-data creation
or attendance changes are not part of the release verification.
