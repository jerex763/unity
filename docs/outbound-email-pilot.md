# Outbound email during the pilot

Unity does **not** send email during the pilot. The People directory and person
profile provide an **Open email app** link. This is a `mailto:` handoff to the
worker's configured email application; composing, sending, delivery, and any
failure all happen outside Unity.

Each email action also shows the address and provides **Copy**. If browser
clipboard access is unavailable or denied, Unity selects the visible address so
the worker can copy it manually. Unity does not claim that a message was sent.

This preserves the existing church-scoped People permissions and does not add a
new disclosure path. Because Unity cannot observe the result of a local email-app
handoff, it does not create a send or delivery audit record.

An in-app sender is out of pilot scope. Reconsider it only after pilot evidence
shows that the handoff is insufficient and the requirements are agreed first:
sender identity, provider, templates, delivery and failure status,
consent/unsubscribe rules, role permissions, retention, and audit history.
No provider, sender configuration, template, delivery tracking, or email audit
implementation is being added now.

## WhatsApp and WeChat handoffs

WhatsApp and WeChat are the primary pilot contact channels. Unity opens `wa.me`
only when a stored number explicitly starts with `+` or `00`; it never guesses a
country code. After that prefix, only ASCII digits, spaces, hyphens, and
parentheses are accepted as human formatting. Removing those separators must
leave an E.164-compatible 1–15 digit number whose first digit is 1–9. Any other
annotation, character, control, or shape is rejected rather than stripped.
Local or ambiguous numbers remain visible and copyable for a manual WhatsApp
handoff. WeChat IDs are likewise visible and copyable because there is no
reliable universal web link for opening a specific WeChat contact.

These actions leave Unity. Unity does not send WhatsApp or WeChat messages and
cannot observe their delivery or failure, so it does not record a message-send
or delivery audit event. Existing church and role permissions still control who
can view the underlying contact details.
