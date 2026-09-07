#!/usr/bin/env bash

set -Eeuo pipefail

# ubuntu-24.04 GitHub-hosted runners include AWS CLI v2. Do not install the
# removed Ubuntu awscli package or silently replace the runner-provided CLI.
if ! command -v aws >/dev/null 2>&1; then
  echo "::error::AWS CLI v2 is missing from the backup runner" >&2
  exit 2
fi
if ! aws_version="$(aws --version 2>/dev/null)" || [[ "${aws_version}" != aws-cli/2.* ]]; then
  echo "::error::AWS CLI v2 could not be verified on the backup runner" >&2
  exit 2
fi

sudo apt-get update
sudo apt-get install --yes age postgresql-client

for tool in age pg_dump curl; do
  if ! command -v "${tool}" >/dev/null 2>&1 || ! "${tool}" --version >/dev/null 2>&1; then
    echo "::error::Required backup tool is unavailable: ${tool}" >&2
    exit 2
  fi
done
echo "Backup tools verified."
