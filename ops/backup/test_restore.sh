#!/usr/bin/env bash

set -Eeuo pipefail

: "${SOURCE_DATABASE_URL:?SOURCE_DATABASE_URL is required}"
: "${TARGET_DATABASE_URL:?TARGET_DATABASE_URL is required}"

command -v age-keygen >/dev/null
command -v psql >/dev/null

work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT

psql "${SOURCE_DATABASE_URL}" <<'SQL'
CREATE TABLE fictional_backup_probe (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    display_name text NOT NULL
);
INSERT INTO fictional_backup_probe (display_name)
VALUES ('Fictional Alpha'), ('Fictional Beta');
SQL

identity_file="${work_dir}/age-identity.txt"
age-keygen --output "${identity_file}" >/dev/null
recipient="$(age-keygen -y "${identity_file}")"
backup_dir="${work_dir}/encrypted"

backup_uri="$(
  DATABASE_URL="${SOURCE_DATABASE_URL}" \
    BACKUP_AGE_RECIPIENT="${recipient}" \
    BACKUP_DESTINATION="file://${backup_dir}" \
    BACKUP_RETENTION_DAYS=30 \
    "$(dirname "$0")/backup.sh"
)"

if grep --text --quiet "Fictional Alpha" "${backup_uri#file://}"; then
  echo "Encrypted backup unexpectedly contains plaintext fixture data." >&2
  exit 1
fi

BACKUP_SOURCE="${backup_uri}" \
  BACKUP_AGE_IDENTITY_FILE="${identity_file}" \
  TARGET_DATABASE_URL="${TARGET_DATABASE_URL}" \
  RESTORE_CONFIRM_NON_PRODUCTION=yes \
  "$(dirname "$0")/restore.sh"

restored_rows="$(
  psql \
    --tuples-only \
    --no-align \
    "${TARGET_DATABASE_URL}" \
    --command "SELECT count(*) FROM fictional_backup_probe;"
)"
restored_name="$(
  psql \
    --tuples-only \
    --no-align \
    "${TARGET_DATABASE_URL}" \
    --command "SELECT display_name FROM fictional_backup_probe ORDER BY id LIMIT 1;"
)"

[[ "${restored_rows}" == "2" ]]
[[ "${restored_name}" == "Fictional Alpha" ]]

echo "Encrypted backup restore test passed with fictional data."
