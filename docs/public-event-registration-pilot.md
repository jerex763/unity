# Public event registration pilot and manual acceptance

Issue #93 adds visitor registration links as an MVP pilot. Every test, screenshot,
demo, evaluation session and manual check in this document **must use fictional
people, contact details, churches and events only**. The checked-in privacy notice
is still a draft; this feature is not approved for formal or real personal data.

## Pilot boundary and required human review

Before any production use with real data, a named human owner must complete and
record a review covering:

1. church legal name, privacy contact, approved notice wording and version;
2. lawful basis/consent design, retention, withdrawal and complaints process;
3. Render region, subprocessors, request-log handling and overseas disclosure;
4. normalized contact collision report before migration (shared phone numbers,
   case-only email duplicates, malformed historical contacts);
5. reverse-proxy client-IP behaviour and rate-limit thresholds under expected load;
6. accessibility and safeguarding review, including the transport request workflow;
7. incident response and link-revocation ownership.

Set `PRIVACY_NOTICE_VERSION` and `PRIVACY_NOTICE_TEXT` from that approved result.
They are the single backend configuration source returned to the public UI and
recorded with consent; do not duplicate notice wording in frontend code.

## Manual acceptance script (fictional data only)

Use two fictional churches, `Fictional Harbour Church` and `Fictional Hills
Church`, and browser profiles that contain no real personal data.

- Create a future, signup-open event as a leader. Generate a public link, copy it,
  open it signed out on 320 px and 375 px viewports, and confirm there is no login
  redirect or horizontal overflow.
- Confirm full name and consent are labelled required. Confirm contact is labelled
  required as a group (email or phone) while its individual fields and transport
  are clearly optional. Confirm no notes, sensitive fields or church directory are
  requested or shown.
- Read the displayed notice and version. Submit without consent, with no contact,
  and with a stale version using developer tools; each must fail without creating a
  registration. Submit valid fictional details and inspect the stored append-only
  self-service consent: status granted, exact configured version, decision time,
  and no staff recorder.
- Register a pre-existing fictional person using differently formatted email and
  phone values. Confirm matching occurs only inside Fictional Harbour Church and
  never reveals whether a person existed. An existing Person may receive a first
  registration only when their latest consent is current, granted self-service
  consent. Otherwise the request is a generic no-op for staff follow-up. Repeat an
  existing registration and confirm the Person, registration, consent decision,
  transport, status and original cancellation credential remain byte-for-byte
  unchanged.
- Fill an event to capacity and submit another fictional visitor request. Confirm
  internally that the existing service assigns the waitlist and signup-close rules
  still apply. The public page must say only that the request was accepted; final
  registered/waitlisted state is verified by authorized workers in the internal
  roster and communicated through the church's approved contact workflow.
- Confirm the accepted page contains only event title, the generic request-accepted
  message, and a private cancellation link—no registered/waitlisted state, roster,
  directory, internal note or contact. This deliberate uniform response prevents
  existing-person and capacity details becoming a public identity oracle. Use the
  cancellation link once, then confirm replay returns the same generic response.
- Rotate the organiser link and verify the old URL fails. Revoke the new URL and
  verify it fails. Confirm raw tokens are absent from database rows and event-list
  API responses.
- Submit rapidly from one test client until HTTP 429. Confirm invalid/revoked links,
  contact conflicts and tenant differences use generic errors suitable for public
  callers. Spoof `X-Forwarded-For` values and confirm they do not bypass the limit
  with the default trusted-proxy setting. Flood random invalid tokens and confirm
  only one client/window counter is created, never one row per invalid token.
- Recheck `/login`, signed-in event registration, roster/check-in, person consent
  administration and protected routes.

Record browser/device, build SHA, tester, date, fictional dataset name, pass/fail,
and redacted screenshots. Never paste a live public or cancellation token into an
issue, analytics event, support chat, or screenshot.

## Evaluation questions and exit criteria

Measure completion and error rates using manual fictional sessions only; the MVP
does not add visitor analytics. Ask testers whether field obligation, privacy
purpose, accepted-response expectations, later status communication, and
cancellation were understandable without staff help.
Exit the pilot only when all automated and manual checks pass, the human reviews
above are signed off, and no high-severity privacy/accessibility finding remains.

## Deployment and residual risks

- Tokens use 256 bits of randomness and only SHA-256 digests are stored. Raw tokens
  necessarily appear in visitor URL paths and may reach browser history or platform
  edge logs. Gunicorn application access logging is disabled. Configure Render edge
  log access/retention and never add request-path logging. Rotation/revocation is the
  response to suspected leak.
- Fixed-window counters are in PostgreSQL, so gunicorn processes and Render instances
  share limits without a paid dependency. Database uncertainty fails closed. This
  adds write load and retains pseudonymous HMAC client digests; schedule deletion of
  expired buckets and identity locks through the included housekeeping command,
  which also runs at deployment. `X-Forwarded-For` is ignored by default. Set
  `PUBLIC_REGISTRATION_TRUSTED_PROXY_HOPS` only after confirming Render's exact
  trusted proxy chain; parsing proceeds from the trusted right side.
- PostgreSQL row locks and normalized unique constraints provide the intended
  concurrency behaviour. SQLite is useful for tests but does not reproduce
  PostgreSQL lock semantics. Run the concurrency acceptance check against staging
  PostgreSQL before production approval.
- Deployment runs `preflight_person_contact_normalization` before migrations.
  Migration `people.0005` independently and atomically rejects historical
  same-church normalized email collisions, reporting only church and Person IDs—not
  email values. A human must resolve those records under the approved lifecycle;
  the migration never guesses, merges, or partially applies.
- Every accepted response has the same shape and a random-looking cancellation URL.
  For a newly created registration it is the real one-time credential; for a no-op
  duplicate/takeover attempt it is a decoy. Cancellation responses are deliberately
  identical for real, invalid, and already-used credentials so contact knowledge
  cannot become registration-management authority.
- Link creation is limited to events whose existing registration service considers
  signup open. Cancellation preserves the existing cancellation rule; it does not
  introduce automatic waitlist promotion because the current product has none.
