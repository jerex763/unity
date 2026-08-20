# Pilot runbook

Use this checklist for Issue
[#32](https://github.com/jerex763/unity/issues/32). The current Render/Neon demo
is fictional-data-only: actual church workers may evaluate it, but every church,
event, participant, contact method, interaction and outcome entered in Unity must
be fictional.

The current worker session is scheduled to be completed by **Friday 2026-08-28
(Australia/Sydney)**. The pilot owner will deliver each worker's distinct
temporary credentials through a direct one-to-one WhatsApp conversation. Do not
use a WhatsApp group, forward credentials, or include credentials in the feedback
record.

## Session shape

Use three separate temporary accounts and ask each worker to test on their own
phone:

| Worker | Account role | Task | Expected time |
|---|---|---|---:|
| Pastor | Pastor | Review the event, permissions and follow-up assignment | 10–15 minutes |
| Check-in worker | Leader | Run event-day check-in and add a fictional visitor | 10–15 minutes |
| Follow-up worker | Leader | Work the assigned fictional follow-up to an outcome | 10–15 minutes |

Give each worker the demo URL and their own temporary credentials through an
agreed private channel. Never place credentials in GitHub, chat transcripts,
shared checklists or screenshots. Tell workers that the session contains no real
participant data and that they must stop rather than enter any.

## Coordinated end-to-end order

Allow about 45–55 minutes for one coordinated session. Each worker's hands-on
portion remains approximately 10–15 minutes.

1. **Briefing — 5 minutes.** State the fictional-data rule, stop conditions and
   private feedback channel. Each worker confirms they received only their own
   account and can sign in on their phone.
2. **Pastor setup check — 5–10 minutes.** The Pastor confirms the fictional
   church/event/roster and that the prepared Person can be edited by the Pastor.
3. **Check-in flow — 10–15 minutes.** The check-in worker completes the prepared
   preregistration, existing-person and new-visitor paths on the dedicated
   check-in page, then verifies the Leader cannot edit People.
4. **Pastor assignment — 5 minutes.** The Pastor confirms the new visitor's
   first-visit follow-up, assigns it to the follow-up worker, and records the
   supplied fictional due date and next action.
5. **Follow-up flow — 10–15 minutes.** The follow-up worker confirms the task is
   scoped to them, checks the fictional WhatsApp/WeChat handoff without sending a
   real message, records the supplied fictional interaction and closes it with
   the supplied fictional outcome.
6. **Feedback and sign-out — 10 minutes.** Ask the five common questions, record
   only workflow themes/device/browser/duration, and confirm all workers sign
   out. Do not clean or disable anything until the separate post-session scope
   and authorization are recorded.

## Team Lead preparation

- Obtain separate authorization for any account creation and fictional-data
  creation that is not already complete. Record the RUN_ID without credentials.
- Confirm the event, preregistration and worker accounts all belong to the same
  fictional church and RUN_ID. Inspect read-only before creating anything else.
- Confirm the deployed commit, `/api/health/`, and the latest CI result for that
  commit. A health response alone does not identify the deployed feature set.
- Run the focused fictional flow and permission tests locally:

  ```bash
  cd backend
  .venv/bin/pytest -q tests/test_pilot_flow.py tests/test_permission_matrix.py
  ```

- Confirm each account has only its intended active role. Do not make a worker a
  Django superuser or share the preserved demo superuser account.
- Prepare a private feedback channel. Feedback must contain workflow themes
  only—no participant, pastoral, care or credential content.
- Name the person who will stop the session if a worker sees the wrong church,
  confidential data or an unexpected edit capability.
- Read `docs/current-event-registration-review-2026-08.md`. Use the current
  Google Form only as workflow context; never copy its responses or real attendee
  details into the demo.

Do not use QR check-in, AI features, care/prayer data, production backup
credentials or real personal data in this session.

## Worker checklists

### Pastor

1. Sign in on the phone and confirm the active church is the fictional pilot
   church.
2. Open the prepared event and confirm its date, registration state and roster
   are the expected fictional records.
3. Open People and confirm the Pastor can view and edit the prepared fictional
   Person. Do not add unplanned data.
4. After the check-in worker completes the new-visitor path, open Follow-ups and
   confirm one first-visit follow-up exists.
5. Assign it to the follow-up worker with a due date and a clear next action.
6. Confirm the assignment appears correctly, then sign out.

### Check-in worker

1. Sign in on the phone and confirm the active church and prepared event.
2. Open the event's dedicated **Check in** page rather than using the
   registration-management screen as the event-day workflow.
3. Check in the prepared fictional preregistration and confirm it shows as
   checked in.
4. Use **Existing person** to find the prepared fictional Person. Confirm the
   result exposes only enough masked information to choose the right record,
   then check that person in without changing their profile.
5. Use **New visitor** for the prepared fictional visitor details. Enter only the
   supplied fictional contact method and confirm the visitor is checked in.
6. Open People and confirm there is no create/edit Person action available to
   the Leader account. If an edit succeeds by any route, stop and report a
   permission incident.
7. Confirm the page fits the phone without horizontal scrolling, then sign out.

### Follow-up worker

1. Sign in on the phone and confirm the active church.
2. Open **My follow-ups** and confirm only the fictional task assigned to this
   worker is visible.
3. Open the task and confirm its person, due date and next action match the
   Pastor's assignment.
4. Try the primary fictional contact handoff (WhatsApp or WeChat as prepared).
   Do not send a real message; return to Unity after confirming the handoff or
   copy action is understandable.
5. Record the supplied fictional interaction, then close the follow-up with the
   supplied fictional outcome.
6. Confirm the closed task no longer appears as open work and sign out.

## Stop conditions

Stop the session immediately and preserve non-sensitive evidence if any worker:

- sees another church's records or confidential care content;
- can perform an action outside the role matrix;
- is asked to enter real participant or credential data;
- cannot identify whether an action changed a record; or
- encounters a mobile layout that blocks completion.

Record the role, page, time, deployed commit and a redacted description. Do not
copy affected record contents into the report.

## Feedback and evidence

Ask each worker the same five questions:

1. Could you complete the task without coaching?
2. Where did you hesitate or lose context?
3. Did you see too much or too little information for your role?
4. What single change would most improve the next session?
5. For student/worker status, study area, industry, future-event notices and
   WhatsApp groups, which answer would cause a real operational action rather
   than merely being interesting to collect?

Record completion/failure, phone/browser, approximate duration and themes in
`docs/pilot-review-2026-07.md`. Do not record names, contact details, message
contents or pastoral information.

## After the authorized session

- Inspect the exact temporary accounts and RUN_ID-tagged fictional records
  read-only. Report counts and scope before changing anything.
- Obtain explicit cleanup authorization. Account disabling/removal and
  fictional-data cleanup must stay within the approved targets; preserve audit
  evidence and the existing demo superuser.
- Perform the isolated non-production backup restore as its own authorized
  operation, then record only aggregate counts, duration and outcome. CI restore
  evidence does not replace this release-gate drill.
- Complete `docs/pilot-review-2026-07.md` and update Issue #32 with redacted
  evidence. Do not close it until every acceptance item is actually satisfied.
- Choose later work from repeated observed friction. Do not automatically
  promote Issues #16 or #22–#25.
