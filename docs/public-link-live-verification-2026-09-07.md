# Live public-link recovery verification — 2026-09-07

The user explicitly authorized creating one clearly fictional test event and its
public link, copying it again after refresh, and opening the registration page.
No registration submission, existing-link replacement, account creation or cleanup
was included.

## Environment and target

- Demo: https://unity-fictional-demo.onrender.com
- Existing authenticated admin session in Fictional Test Church.
- Local HEAD and GitHub branch `codex/mvp-next`: `5c665d1` (remote verified).
- Test event ID: **9**.
- Title: **FICTIONAL TEST — Public link recovery 20260907**.
- Start/end: 14 September 2026, 18:00–19:00 in the browser's local time.
- Location and description explicitly identify a fictional test, not a gathering.
- Capacity: 1; no signup submitted.

## Observed results

1. Saved the new event; its card showed registration open and 0/1 registered.
2. Created its public link; the UI confirmed the link was ready.
3. Used Copy link; the UI confirmed copying and the clipboard held a URL on the
   expected demo registration route.
4. Fully reloaded Events. The persisted event still exposed Copy link.
5. Used Copy link again. The UI confirmed copying and an in-memory exact string
   comparison with the first copied URL returned **true**.
6. Opened the recovered URL in another tab. The registration page displayed the
   exact test-event title, time, fictional location and description, plus an empty
   registration form. No fields were completed and Register was not clicked.

The key itself was never read. Public URLs/tokens were held only in the browser
session for comparison/navigation and are omitted from this record.

## Limits and retained state

This verifies live encryption and later recovery of one newly created link with
the current configuration. It does not establish key backup/custody, rotation,
legacy-link recoverability, or end-to-end registration submission. The browser
session was authenticated; this was not an anonymous-session acceptance test.

The original pilot event #8 and its existing public link were not modified.
Test event #9 and its public link remain available, with cleanup requiring separate
authorization. No account or person data was created.

The browser automation's initial datetime fill did not reach React form state;
native keyboard changes committed the values before saving. This is an observed
automation limitation, not sufficient evidence of a human-facing date-input defect.

Next release priority remains #99: verify backup infrastructure configuration and
prepare a specifically authorized encrypted backup/isolated restore drill. The
backup schedule remains paused. This verification does not close the pilot gate.
