#!/usr/bin/env bash

set -Eeuo pipefail

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Required environment variable is missing: ${name}" >&2
    exit 2
  fi
}

alert_failure() {
  local exit_code=$?
  if [[ -n "${BACKUP_ALERT_WEBHOOK_URL:-}" ]]; then
    curl --fail --silent --show-error \
      --max-time 15 \
      --header "Content-Type: application/json" \
      --data '{"text":"Unity database backup failed. Check the protected backup job logs."}' \
      "${BACKUP_ALERT_WEBHOOK_URL}" >/dev/null || true
  fi
  exit "${exit_code}"
}

cleanup() {
  rm -rf "${work_dir:-}"
}

trap alert_failure ERR
trap cleanup EXIT

require_env DATABASE_URL
require_env BACKUP_AGE_RECIPIENT
require_env BACKUP_DESTINATION

command -v age >/dev/null
command -v pg_dump >/dev/null

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
filename="unity-${timestamp}.dump.age"
work_dir="$(mktemp -d)"
encrypted_backup="${work_dir}/${filename}"

pg_dump \
  --format=custom \
  --no-owner \
  --no-acl \
  "${DATABASE_URL}" |
  age \
    --encrypt \
    --recipient "${BACKUP_AGE_RECIPIENT}" \
    --output "${encrypted_backup}"

case "${BACKUP_DESTINATION}" in
  file://*)
    destination_dir="${BACKUP_DESTINATION#file://}"
    mkdir -p "${destination_dir}"
    chmod 700 "${destination_dir}"
    destination="${destination_dir%/}/${filename}"
    install -m 600 "${encrypted_backup}" "${destination}"
    find "${destination_dir}" \
      -type f \
      -name "unity-*.dump.age" \
      -mtime "+${BACKUP_RETENTION_DAYS:-30}" \
      -delete
    backup_uri="file://${destination}"
    ;;
  s3://*)
    command -v aws >/dev/null
    backup_uri="${BACKUP_DESTINATION%/}/${filename}"
    aws s3 cp \
      --only-show-errors \
      --sse AES256 \
      "${encrypted_backup}" \
      "${backup_uri}"
    ;;
  *)
    echo "BACKUP_DESTINATION must start with file:// or s3://" >&2
    exit 2
    ;;
esac

echo "${backup_uri}"
