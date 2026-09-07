#!/usr/bin/env bash

set -Eeuo pipefail

# Production-only preflight. backup.sh also supports local file:// restore drills.
# Report configuration names only; never echo their values or contact services.
missing=0
for name in DATABASE_URL BACKUP_AGE_RECIPIENT BACKUP_DESTINATION \
  AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION \
  BACKUP_ALERT_WEBHOOK_URL; do
  value="${!name:-}"
  if [[ -z "${value//[[:space:]]/}" ]]; then
    echo "::error::Required backup configuration is missing: ${name}" >&2
    missing=1
  fi
done
if [[ "${missing}" -ne 0 ]]; then
  exit 2
fi
if [[ "${BACKUP_DESTINATION}" != s3://?* ]]; then
  echo "::error::BACKUP_DESTINATION must be a non-empty S3 destination" >&2
  exit 2
fi
echo "Production backup configuration names are present; connectivity is not checked."
