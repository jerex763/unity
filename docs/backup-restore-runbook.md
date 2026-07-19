# Database backup and restore runbook

## Policy

Unity is designed to create one encrypted PostgreSQL backup every day. The daily
schedule is paused under Issue #99 until the production database, private object
storage, encryption recipient and failure alert are configured and a manual
backup/restore drill succeeds. Once enabled, backups are retained for 30 days in
private object storage. This gives an initial recovery point objective of 24
hours; the team must set an explicit recovery time objective after the first
production-sized restore.

Backups must contain only fictional data until the M0 exit gate passes. The
scheduled workflow is not ready for production until every setup check below is
complete.

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
