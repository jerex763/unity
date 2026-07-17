# Pilot review — July 2026

Issue: [#32](https://github.com/jerex763/unity/issues/32)

## Current status

The fictional rehearsal is complete. The controlled real activity and worker
feedback are pending; this review must not be marked complete until those happen.

| Gate | Evidence | Status |
|---|---|---|
| Signup → manual check-in → walk-in → follow-up → outcome | `backend/tests/test_pilot_flow.py` | Passed with fictional data |
| Cross-church and confidential access | `backend/tests/test_permission_matrix.py` plus role-specific API tests | Passed with fictional data |
| Encrypted backup restore | Pull-request **Backup restore** check using PostgreSQL 16 and fictional probes | Passed in CI |
| Mobile worker use | Controlled activity with 2–3 actual workers | Pending |
| Real activity | One small church activity with minimum necessary data | Pending |
| AI release safety | No AI feature is in the pilot scope | Passed |

## Controlled activity record

- Date and activity:
- Pilot owner:
- Workers and roles (do not list participant details):
- Software version / commit:
- Backup timestamp restored:
- Restore duration and outcome:
- Permission or audit findings:

## Worker feedback

Record themes without personal or pastoral content.

| Worker role | What worked | Friction or failure | Suggested change |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## What worked

- Pending controlled activity.

## What failed

- Pending controlled activity.

## Recommendation

Keep QR check-in and Groups & Care in the later backlog until the controlled
activity supplies evidence. After the pilot, recommend only the smallest issue
that addresses a repeated operational need. Any AI proposal requires a separate
evaluation set, human-review workflow, permission analysis, and safe fallback.
