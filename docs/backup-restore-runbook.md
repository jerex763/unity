# Database backup and restore runbook

## Policy

Current policy, 2026-09-17: use the manual, no-new-fee procedure below for the
fictional-data demo. Paid AWS setup is deferred and the GitHub backup schedule
remains disabled. This policy does not authorize importing real participant data.

The selected online snapshot `20260914T132526Z` restored successfully: 28 tables,
408 rows, matching table digests and passing Django/migration checks. The private
Google Drive copy passed download SHA-256 comparison. A user-confirmed externally
retrieved age identity decrypted the backup; the separately supplied application
key decrypted both public-link ciphertexts after isolated restoration. External
custody of that application key has not been independently verified. These are
point-in-time results, not evidence of automatic recurring backups or alerts.

## Manual cadence for the fictional pilot

- After each session that changes fictional business data, take an encrypted
  backup and complete the Drive copy verification before closing the session.
- Before a database migration, data repair/deletion or encryption-key rotation,
  verify a current recoverable backup. This does not grant authorization for the
  migration, deletion or rotation itself. Documentation-only commits need no dump.
- Once per week during active testing, the project owner checks the backup log.
  If data changed since the last verified snapshot, complete a new backup. If no
  data changed, record that fact; repeated identical dumps add little value.
- Restore a selected retained snapshot once per month during active testing, and
  after backup tooling or encryption-key changes. Each execution remains a scoped
  action; this runbook creates no scheduled job or unattended authorization.

The user is the operational owner; Codex can execute a requested session. No
background monitoring or reminders are currently configured. Recovery coverage
ends at the most recent verified snapshot, so changes since then can be lost.
The longer-term daily/24-hour objective is not achieved by this manual policy.
Reassess cadence, storage, key access and failure notification before real-data use.

## Completion checklist for each manual backup

1. Confirm source is the fictional demo using read-only checks. Never reuse the
   restore target as an online source or restore over the online database.
2. Create a dated encrypted artifact outside Git, keeping age/application keys
   separately protected. Retain the decryption keys required by older snapshots.
3. Record timestamp, encrypted byte size and SHA-256 in a non-secret manifest.
4. Upload only ciphertext and the non-secret manifest into the private Drive
   backup folder; verify owner-only/Restricted access for the new files.
5. Download the ciphertext and compare its SHA-256 to the local verified artifact.
6. Mark the run complete only after verification; restore drills additionally
   check table contents, migrations and application-link decryptability in a
   private local target. Never report tokens or participant records.

Maintain at least the latest verified backup and its predecessor while the
manual pilot is active. Review older artifacts after 30 days; deletion remains
separately authorized. Keep required old keys until their snapshots are retired.
Do not point the existing local backup script at the verified archive directory
without considering its automatic `BACKUP_RETENTION_DAYS` deletion behavior;
use a new dated destination for each manual run.

If a run fails, record the failed stage without secrets, retain the last known
successful backup, and report the failure in the current task. Do not label the
attempt successful because upload alone completed. Postpone planned destructive
work until recovery verification succeeds. There is no unattended failure alert.

Backup log fields: snapshot UTC time, source/environment label, operator,
ciphertext byte size/hash, private storage location, download-check result,
last restore result, key-custody confirmation and unresolved failure. Never store
connection strings, key values or raw public links in the log.

## Future automated production policy (deferred)

The intended daily encrypted backup and 30-day retention policy is a future
objective under #99. Establish storage, protected key custody, failure delivery,
retention, and tested recovery before enabling automation; set recovery-time
expectations from a representative restore. The AWS steps below are historical
implementation guidance, not an instruction to sign up or spend money now.

## Workflow prerequisite repair (#99)

The bounded prerequisite repair uses the GitHub-hosted `ubuntu-24.04` image's
preinstalled AWS CLI v2, verifies that it runs, and installs only the remaining
backup tools through apt. It must fail clearly if the runner no longer provides
that CLI rather than silently downloading an unverified replacement. GitHub's
[Ubuntu 24.04 image inventory](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md)
lists the bundled AWS CLI; the exact patch version follows image updates.

Configuration preflight checks the required database, encryption recipient,
S3 destination, AWS identity/region and alert settings before tool installation
or database access. Errors identify missing variable names, never values.
Passing preflight confirms presence only: it does not establish credential
validity, bucket privacy/lifecycle, key custody, alert delivery or recoverability.
The daily schedule stays paused and the operational setup below still applies.

## One-time production setup

1. Create a dedicated private S3 bucket or prefix. Enable block-public-access,
   access logging and object versioning. Do not grant list/read access to the web
   application role.
2. Apply the 30-day lifecycle:

   ```bash
   aws s3api put-bucket-lifecycle-configuration \
     --bucket YOUR_PRIVATE_BACKUP_BUCKET \
     --lifecycle-configuration file://ops/backup/s3-lifecycle.json
   ```

3. Create a dedicated backup identity allowed only to put objects under the
   `unity/` prefix. Restore operators use a separate read-only identity. Keep
   bucket administration separate from both.
4. Generate an age identity on an offline administrator machine:

   ```bash
   age-keygen -o unity-backup-identity.txt
   age-keygen -y unity-backup-identity.txt
   ```

   Store the private identity in the approved password/secret manager and an
   offline recovery copy. GitHub receives only the public `age1...` recipient.
5. Create a protected GitHub environment named `production-backup`. Restrict
   environment administration and add:

   - `BACKUP_DATABASE_URL`
   - `BACKUP_AGE_RECIPIENT` (public recipient)
   - `BACKUP_S3_URI` (for example `s3://private-bucket/unity`)
   - `BACKUP_AWS_ACCESS_KEY_ID`
   - `BACKUP_AWS_SECRET_ACCESS_KEY`
   - `BACKUP_AWS_REGION`
   - `BACKUP_ALERT_WEBHOOK_URL`

6. Resolve Issue #99 and run **Production database backup** manually. Confirm an
   `.dump.age` object exists, is private, has server-side encryption metadata and
   is covered by the lifecycle rule. Trigger a controlled failure and confirm the
   operations channel receives the generic failure alert.
7. Restore the encrypted object into an isolated non-production database and
   record the result. Only then re-enable the daily schedule in
   `.github/workflows/backup.yml`.

When enabled, the intended schedule runs daily at 15:17 UTC. GitHub workflow
access, object-store access, age private-key access and alert-channel membership
must be reviewed quarterly and whenever a maintainer leaves.

## Restore into non-production

Never restore directly over production. Create an isolated target with no public
network access and verify it contains no real data unless the restoration is an
authorized incident operation.

```bash
export BACKUP_SOURCE=s3://private-bucket/unity/unity-YYYYMMDDTHHMMSSZ.dump.age
export BACKUP_AGE_IDENTITY_FILE=/secure/path/unity-backup-identity.txt
export TARGET_DATABASE_URL=postgresql://.../unity_restore
export PRODUCTION_DATABASE_URL=postgresql://.../unity
export RESTORE_CONFIRM_NON_PRODUCTION=yes
ops/backup/restore.sh
```

After restoration:

1. Run Django migrations and `python manage.py check`.
2. Compare expected tenant and record counts without exporting sensitive rows.
3. Confirm authentication is disabled or passwords are reset in the restored
   environment.
4. Record the backup timestamp, restore duration, operator and outcome.
5. Destroy the restored environment after the test or incident review.

## Automated restore evidence

CI starts separate PostgreSQL 16 source and restore databases, inserts two
fictional probe rows, creates a fresh age key, encrypts a custom-format dump,
restores it and verifies both rows. It also checks that the encrypted file does
not expose the fictional plaintext. This runs on every pull request so recovery
does not silently regress.

## Local full-schema evidence (2026-09-14)

A fresh PostgreSQL 16.14 database was migrated and populated with synthetic
church, inactive user, person, event, registration and attendance audit data.
The existing backup/restore scripts with age 1.2.1 restored 28 public tables;
all 129 serialized application records matched exactly, migration checks and
Django system checks passed. The encrypted file did not contain the synthetic
name marker. The 0.39-second restore measures a tiny fixture only. Both databases
used a private local Unix socket, and the temporary cluster, backup and identity
were removed after the drill. No online database was accessed. This establishes
local full-schema script compatibility, not an operational backup or successful
recovery of an online public link. The separate key requirement below remains.

## Public-link encryption keys and restoration

Online fictional-database drill on 2026-09-14: backup `20260914T132526Z` restored
all 28 public tables and 408 rows with identical per-table counts and SHA-256
content digests after normalizing timezone and row ordering. Source queries and
pg_dump used the same exported read-only snapshot. Attendance audit assertions,
migration checks and Django system checks passed. The encrypted artifact and
verification manifest are retained under the private local UnityBackups folder;
the age identity is stored separately under the private unity-backup configuration
folder. The isolated restored cluster was removed. Both artifact and identity
are still on the same computer; off-device recovery custody is not established.
Public-link token decryption was not part of this drill.

Recoverable public links add encrypted token material to the database. Their
`PUBLIC_LINK_ENCRYPTION_KEYS` belong in a separately protected secret manager
and offline recovery copy, not the S3 backup objects or repository. A database
restore alone cannot prove public-link recovery works: a separately authorized
isolated drill needs the corresponding retained decryption key as well.
Preserve old keys for retained backups even after a live-key migration. Existing
public URL validation uses the stored digest independently of decryption.
Never log recovered links during a restore drill, and never make the restored
application publicly accessible merely to test decryption.
