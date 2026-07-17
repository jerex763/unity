#!/usr/bin/env bash

set -Eeuo pipefail

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Required environment variable is missing: ${name}" >&2
    exit 2
  fi
}

cleanup() {
  rm -rf "${work_dir:-}"
}

trap cleanup EXIT

require_env BACKUP_SOURCE
require_env BACKUP_AGE_IDENTITY_FILE
require_env TARGET_DATABASE_URL

if [[ "${RESTORE_CONFIRM_NON_PRODUCTION:-}" != "yes" ]]; then
  echo "Set RESTORE_CONFIRM_NON_PRODUCTION=yes after verifying the target." >&2
  exit 2
fi
if [[ -n "${PRODUCTION_DATABASE_URL:-}" ]] &&
  [[ "${TARGET_DATABASE_URL}" == "${PRODUCTION_DATABASE_URL}" ]]; then
  echo "Refusing to restore over the configured production database." >&2
  exit 2
fi

command -v age >/dev/null
command -v pg_restore >/dev/null

work_dir="$(mktemp -d)"
encrypted_backup="${work_dir}/backup.dump.age"

case "${BACKUP_SOURCE}" in
  file://*)
    cp "${BACKUP_SOURCE#file://}" "${encrypted_backup}"
    ;;
  s3://*)
    command -v aws >/dev/null
    aws s3 cp --only-show-errors "${BACKUP_SOURCE}" "${encrypted_backup}"
    ;;
  *)
    echo "BACKUP_SOURCE must start with file:// or s3://" >&2
    exit 2
    ;;
esac

age \
  --decrypt \
  --identity "${BACKUP_AGE_IDENTITY_FILE}" \
  "${encrypted_backup}" |
  pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --no-acl \
    --exit-on-error \
    --dbname "${TARGET_DATABASE_URL}"
