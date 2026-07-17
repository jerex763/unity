# Person data lifecycle

Unity does not use routine hard deletion for people. The normal action is
**deactivate**, followed by **anonymize** only when approved. Hard deletion is an
exceptional admin operation with a controlled reason code.

## Deactivate

Leaders, pastors and admins may deactivate a person. Deactivation sets
`membership_status=inactive` and records `deactivated_at`; the Person and all
event, group, follow-up, care, interaction and consent history remain unchanged.
The Django Admin exposes deactivation as its lifecycle action and does not expose
the standard delete action.

## Anonymize

Only church admins may anonymize. The operation is transactional and:

- replaces the name with `Anonymized person <id>`;
- clears preferred name, birth date, email, phone, photo, country, suburb,
  occupation, university, course, interests, household, inviter, faith
  background, discipleship stage and person notes;
- resets gender and WhatsApp flags, marks the person inactive and timestamps the
  anonymization;
- removes relationship rows and inbound `invited_by` links;
- clears event-registration notes and follow-up outcomes;
- replaces care titles, clears care details/confidential flags and clears
  interaction summaries;
- disables and unlinks any authentication membership associated with the Person.

Event registrations, group memberships, follow-up shells, care workflow shells,
interaction timestamps and consent-decision history remain linked to the
anonymized Person ID. This preserves aggregate and operational history without
retaining the removed free text.

Audit events retain action, actor, church, request ID and the historical numeric
target ID. They never receive the cleared field values.

## Hard delete

Only an active church admin with the `manage_destructive` capability may call the
hard-delete endpoint. The request must supply one of:

- `created_in_error`
- `duplicate`
- `legal_request`
- `test_data`

Hard deletion cascades to relationships, registrations, group memberships,
follow-ups, care cases, interactions and consent records. Authentication
memberships unlink through their foreign-key rule. The pre-delete audit event
survives because it stores a target type and numeric ID rather than a Person
foreign key.

Hard deletion should occur only after confirming backups, legal/privacy
obligations and the intended effect on related records. Never place names, contact
details or case notes in the reason.
