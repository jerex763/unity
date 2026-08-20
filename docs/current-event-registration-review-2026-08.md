# Current event registration form review — August 2026

Reviewed on 2026-08-21 against the public Google Form for **AI: A Christian's
Context**:

<https://docs.google.com/forms/d/e/1FAIpQLScq--wp93JAzUH6cQFAr4GvMDJrwAlaGsDl-IgcnszSH0iOKg/viewform>

This is a product comparison only. Do not copy current responses or real attendee
data into the fictional Render/Neon demo.

## Visible form fields and Unity mapping

| Current form | Required | Unity today | Product decision |
|---|---:|---|---|
| Name | Yes | Public registration requires full name | Keep Unity behavior |
| Mobile number for a WhatsApp group | Yes | At least one of email, phone or WeChat; optional WhatsApp flag and preferred channel | Keep flexible contact; group membership needs separate specific consent |
| UTS/USYD/other student/worker status | Yes | Person has university and occupation fields, but public registration does not collect them | Treat as a pilot hypothesis, not an immediate feature |
| Attending/cannot attend/maybe | Yes, multi-select | A submission is an affirmative registration; private link supports later cancellation | Keep Unity's unambiguous registration state |
| Notify me of other events | Part of the attendance multi-select | No durable future-events subscription | Any future subscription must be separate, optional and withdrawable |
| Area of study | No | Person has course/university fields, not exposed publicly | Collect only if repeated worker evidence shows an operational need |
| Industry/expertise | No | Person has occupation, not exposed publicly | Same as study information |
| Religious background | No | Person has protected faith background, not exposed publicly | Do not add to event registration now |

Unity also provides event description, capacity/waitlist handling, generic public
responses that avoid identity disclosure, a private cancellation link, actual
check-in state, first-visit follow-up on check-in, tenant scoping, and recorded
privacy consent. Those are not visible in the current Google Form workflow.

## Decisions and risks

### WhatsApp group consent

Marking that a phone number uses WhatsApp or selecting WhatsApp as a preferred
channel is not consent to add the person to a group where other members may see
their number. Before real use, group addition needs separate, specific wording
covering purpose, member visibility, administrators, exit method and end-of-event
handling. It must not be inferred from supplying a phone number.

### Attendance meaning

The current form uses checkboxes, so contradictory choices such as attending and
cannot attend can be selected together. Unity should continue treating public
submission as affirmative registration and cancellation as a separate action.
Do not add `maybe` or `cannot attend` unless pilot evidence shows a distinct
operational workflow that consumes those states.

### Audience context

Student/worker status, institution, course and industry may be useful for the
international-student ministry, but one event is not enough evidence for a form
builder or permanent profile enrichment. During the controlled pilot, ask
workers what action they would take from each answer. If the answer affects only
one event, prefer an event-scoped answer over silently changing an existing
Person profile. Never overwrite a matched Person during public registration.

### Future-event contact

`Please notify me of other events` is broader than administering the current
registration. If supported later, it requires its own optional, auditable and
withdrawable communication preference with a defined channel and owner.

### Religious background

Religious background is sensitive information. The current purpose statement—
understanding attendee needs—is too broad to justify adding it to Unity's public
registration. If a later evidence-backed workflow genuinely requires it, define
the exact use, separate consent, Pastor/Admin-only access, retention, withdrawal,
and a safe non-response path before design or implementation. Do not store it in
an ordinary registration note or expose it to check-in workers.

## MVP recommendation

Do not change code from this comparison alone. Run the three-worker fictional
mobile pilot first. Use the feedback record to decide whether WhatsApp group
consent or a small set of event-scoped audience questions is the next smallest
valuable change. Do not build a general Google Forms-style form builder before
repeated evidence.
