# Backup setup read-only audit — 2026-09-08

Scope: inspect workflow, configuration metadata and existing results. No database
copy, restore, notification, infrastructure mutation or schedule enablement.

## Verified

- GitHub environment `production-backup` exists.
- Its API response has `protection_rules: []` and
  `deployment_branch_policy: null`.
- Latest three backup runs remain failures: 29694284982, 29651414464,
  29596698369 (19, 18 and 17 July 2026).
- The workflow has manual dispatch only; daily scheduling remains paused.
- Environment secret metadata query returned 403. After user login, authenticated
  GitHub settings confirmed **no environment secrets** in `production-backup`
  and **no repository secrets** on the Actions secrets page. Environment variables
  are also empty. No secret values were accessed.
- Thus none of the seven required settings is provided in these secret scopes:
  `BACKUP_DATABASE_URL`, `BACKUP_AGE_RECIPIENT`, `BACKUP_S3_URI`,
  `BACKUP_AWS_ACCESS_KEY_ID`, `BACKUP_AWS_SECRET_ACCESS_KEY`,
  `BACKUP_AWS_REGION`, `BACKUP_ALERT_WEBHOOK_URL`.
- The lifecycle template has current-object expiry after 30 days and incomplete
  multipart upload cleanup, but no noncurrent-version expiry. Since the runbook
  requires versioning, this template alone does not enforce deletion of retained
  object versions after 30 days. Actual bucket rules were not inspected.

## Unknown and next verification

Subsequent user decision: no AWS account/setup exists and no new paid service is
wanted at this stage. The cloud steps below are deferred, not immediate tasks.
No local database backup or restore was run or authorized by this audit.

1. Establish whether a dedicated AWS S3 backup destination already exists. Prepare
   the seven missing settings without exposing values; account, credential and
   infrastructure creation require their separately scoped authorization.
2. Verify the destination's privacy, backup-writer/read-only-restorer separation,
   encryption, versioning, and current/noncurrent retention rules.
3. Confirm age private-key custody and the separately stored public-link keys.
4. Confirm the intended alert destination before any test message.
5. Prepare exact source, destination and isolated restore target for separate
   backup/restore authorization. Do not dispatch the current workflow as a
   configuration probe: it can copy data or send a failure notification.

Missing secrets are now confirmed by authenticated UI, not inferred from 403. No real-data
migration from Google Forms/Sheets is included. Existing local user changes and
`output/` were preserved; no commit or push was performed.
