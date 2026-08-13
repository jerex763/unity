# Outbound email during the pilot

Unity does **not** send email during the pilot. The People directory and person
profile provide an **Open email app** link. This is a `mailto:` handoff to the
worker's configured email application; composing, sending, delivery, and any
failure all happen outside Unity.

Each email action also shows the address and provides **Copy email**. If browser
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
