# Recoverable public registration links — design

Status: user approved implementation after reviewing this proposal. Backend and
frontend are implemented locally; migrations are tested only in isolation. No
agent-side production key provisioning, live link rotation, push or deployment
was performed. The user subsequently authorized a local commit and reported
configuring the key; its hidden value has not been independently validated. Final verification evidence appears below.

## Current facts

PublicRegistrationLink stores only SHA-256 token_digest. The raw random token is
returned on creation and kept in EventsPage memory. There is no recovery GET.
Existing creation/replacement/revocation is available to active same-church
Admin, Pastor and Leader through LEAD_MINISTRY. HasEventAccess currently allows
safe reads for ordinary Members, so adding GET under that permission unchanged
would incorrectly extend access. Use an explicit management-capability check.

## Alternatives

| Choice | Benefit | Cost / limitation |
|---|---|---|
| Keep one-time reveal with clearer copy guidance | No new recoverable secret storage | Does not solve cross-device or forgotten-link recovery |
| Persist in browser storage | Small frontend change | Lost on another device, stale after rotation; persistent browser exposure |
| Server-side encrypted token plus existing digest | Authorized workers can retrieve the same URL across sessions | Requires separate encryption key custody and recovery plan |

Recommended: server-side authenticated encryption, preserving random tokens and
digest-based public validation. A plaintext token column is unnecessary exposure.
Use the maintained cryptography Fernet/MultiFernet implementation rather than
custom cryptography: https://cryptography.io/en/stable/fernet/ . MultiFernet
supports key rollover; application link replacement is a separate operation.

## Concrete behavior

- Keep Copy link and Show link in the existing event controls. Fetch on explicit
  action, show pending/retry, retain manual copy fallback if clipboard fails.
- Copy/reveal never rotates or revokes a link. Keep Replace public link as a
  separate confirmed action explaining that already-shared URLs stop working.
- Authorize recovery to the same active-church management roles that can create
  the link: Admin/Pastor/Leader. Member/anonymous denied; other church IDs 404.
- Add nullable encrypted_token to the link record. New creation stores digest
  and ciphertext atomically. Decryption verifies the resulting digest and bound
  church/event context before returning a URL built from a trusted origin.
- Use a dedicated production encryption key/keyring, separate from Django's
  session signing key. Do not persist raw URLs in frontend storage, event-list
  responses, logs, audit payloads or telemetry. Recovery response: no-store.
- Audit successful recovery by actor/event only, never the token or URL.
- Revocation clears ciphertext. Replacement atomically replaces digest and
  ciphertext; a concurrent recovery must not resurrect an old link. A link
  already copied just before replacement is invalidated normally.
- Missing/wrong keys or corrupt ciphertext produce a generic recoverability
  error; do not automatically replace links. Digest validation of already-shared
  URLs continues independently of the decryption key.
- Closed-event and revoked states clearly say registration is unavailable;
  recovery must not reopen registration.

## Legacy records

Existing links have no ciphertext and cannot be reconstructed from the digest.
The migration must preserve their validity and mark recovery unavailable. Show:
“This older link cannot be displayed again. Find your saved copy or replace it;
replacing it disables the old link.” No automatic backfill by regeneration.
Importing a user-supplied old URL is deliberately outside the first version.

## Conditions and acceptance

This recommendation assumes repeat sharing by event organizers is common enough
to justify key management. If the service cannot retain/recover a dedicated key,
keep one-time reveal and clearer instructions rather than deploy fragile recovery.
Key setup belongs to the deployment plan; never request its value in chat.

Before release verify: same URL after refresh/new session; role and tenant denial;
no list/cache/log exposure; legacy tokens still valid; missing/corrupt key failure;
revocation/replacement and concurrency; encryption-key rollover; mobile pending,
retry and clipboard fallback. Include the new key in the operational recovery
plan without storing it alongside database backups. Backend permission/storage
changes require independent review. UI state previews precede any substantive
layout redesign; this proposal retains the existing event controls.

## Implementation and verification

- GET recovery now enforces LEAD_MINISTRY for Admin/Pastor/Leader, scopes the
  event to the active church, audits identifiers only, and returns no-store.
- Nullable encrypted storage and the audit action have additive migrations.
  Legacy migration test confirms digest/revocation preservation. Missing or
  invalid keys fail management actions without invalidating existing public URLs.
- Fernet payload binds church/event and verifies the digest. All recovery,
  replacement and revocation operations share Event locking; recovery never
  writes stale ciphertext. Revocation clears ciphertext.
- Frontend requests fresh data for Show/Copy, has per-event pending guards,
  discards late results on user/church/role change, and reveals a selectable URL
  if clipboard access fails. No persistent browser URL storage was added.
- Pre-implementation state mock: `ui-mockups/public-link-recovery.html`; five
  target widths checked and 390px preview inspected. This follows the user's
  existing Team Lead design delegation and approval of the concrete behavior.
- Full isolated PostgreSQL 16 suite: **305 passed**, including four row-lock
  concurrency cases. A historical migration test required schema restoration
  after its assertions; that isolation fix preserves the historical test.
- Independent review: **ACCEPT**, including an independent PostgreSQL recovery /
  migration run **32 passed** and frontend focused run **9 passed**.
- Full integrated Playwright suite: **75 passed**, covering 320/375/390/430 and
  desktop. This adds 10 link-recovery browser cases to existing flows.
- Operational deployment and key/backup custody remain unverified. Provision a
  dedicated valid Fernet key before publishing, since new creation/replacement
  fails closed without it. Do not infer production readiness from these tests.

- Final integrated frontend checks: formatting, ESLint, all **130 unit tests**,
  TypeScript and production build passed. Backend Black/Ruff, Django checks and
  migration drift check passed. Local assets: `index-BwfoW3yg.js` and `index-De9yAWE-.css`.

- Actual screenshots and measured layout evidence are stored in
  `public-link-recovery-evidence/`: ready, legacy and transient-error states at
  320/390/1280 have no horizontal page overflow. Mobile ready/legacy screenshots
  were inspected. A discovered below-navigation result issue was fixed by
  focusing/scrolling the result region; new browser assertions require the whole
  result to clear both navigation bars. Independent re-review accepted the fix.
- Temporary PostgreSQL and dev-server processes used for this delivery are
  stopped after verification. No user-owned output or live service was changed.
