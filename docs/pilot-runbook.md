# Pilot runbook

Use this checklist for Issue
[#32](https://github.com/jerex763/unity/issues/32). Keep the first live pilot
small and enter only the minimum necessary personal data.

## Before the activity

- Confirm the activity owner and two or three workers who consent to test Unity.
- Use a non-production rehearsal first and run
  `pytest tests/test_pilot_flow.py tests/test_permission_matrix.py`.
- Confirm the latest **Backend**, **Frontend**, and **Backup restore** checks are
  green on `main`.
- Review worker roles. Give each person the least-privileged active membership
  needed for their task.
- Create the event, confirm signup settings, and prepare one fictional walk-in
  rehearsal.
- Tell workers where feedback will be recorded and who to contact if they see
  data they should not see.

## During the activity

1. Register one participant through the normal signup flow.
2. On a worker's phone, open the registration list and manually check them in.
3. Add one consenting walk-in using only the fields needed for follow-up.
4. Confirm one open follow-up was created for the first-time visitor.
5. Assign it, set a due date, and confirm it appears on that worker's home page.
6. Record one interaction, then close the follow-up with an outcome.
7. Stop and record an incident immediately if church scoping or confidential
   visibility looks wrong.

Do not use QR check-in, AI features, production backup credentials, or care/prayer
data in this pilot.

## After the activity

- Ask each worker what worked, what slowed them down, and what they would change.
- Review role assignments, confidential access, and append-only audit records.
- Restore the latest encrypted backup into an isolated non-production database,
  run Django checks, compare aggregate counts, reset access, and destroy the
  restored environment afterward.
- Complete `docs/pilot-review-2026-07.md` without copying sensitive notes or
  personal details into Git.
- Choose later work from evidence. Do not automatically promote Issues #16 or
  #22–#25.
