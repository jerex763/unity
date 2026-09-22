# Pilot permission evidence — 2026-09-17

Reviewed `4872693` on `codex/mvp-next` following the completed recovery work.
No application change or online data operation was needed.

## Fresh bounded verification

Executed with `TEST_DATABASE_URL` unset, `config.settings.test`, and SQLite in
memory: permission matrix, person lifecycle, follow-up API and attendance audit
suites. Result: **78 passed, 1 skipped, 115 warnings**. The skipped attendance
concurrency test requires PostgreSQL; this run makes no fresh row-lock claim.
Warnings were not independently audited.

| Boundary | Evidence covered |
|---|---|
| Sensitive person operations / cross-church IDs | Role allow/deny matrix and cross-church endpoint regressions |
| Leader visibility | Own-group vs unrelated people; unrelated deactivation denied without mutation |
| Follow-up scope | Assigned/unassigned role matrix and follow-up API suite |
| Confidential care | Forbidden records and fields excluded from server querysets; this is not a new live care-UI test |
| Attendance denial | Member denied (403), other church denied (404), cancelled registration rejected (400), no success audit emitted |
| Attendance integrity | Attribution, idempotency, and audit-failure rollback regressions; earlier live pair evidence remains separately recorded |

No failure was found in this scope. The bounded live attendance test plus these
regressions support fictional-demo acceptance. They do not reconstruct the old
worker session or prove a later real activity had no unauthorized access.

## Release decision

- No additional code or repeat human session is justified by this review alone.
- Keep #32 open: a real-attendee activity, its owner/date/minimal dataset and
  activity-specific access review have not been authorized or completed.
- Backup and public-link recovery have passed their recorded drills; no need
  to repeat them merely to reconcile old documentation.
- Confirm separate custody of the application public-link key, and demonstrate
  the agreed manual backup routine before relying on it for real data.
- Temporary online accounts/data remain retained. Cleanup is a separate decision.
- Keep new modules and broader UI redesign deferred until a concrete need exists.

This closes the current automated permission review, not the real-data pilot
gate. Follow-up inspection confirmed CI for `4872693` completed successfully;
prior `8f0d8e5` CI also succeeded. No deployment success is inferred from a push.
The next pilot decision sheet is in `pilot-runbook.md`; it is preparation, not
authorization for real-data use.
