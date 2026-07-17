# Permission and privacy matrix

This matrix is the authorization contract for Unity APIs. Server-side querysets
and serializers enforce it; hiding a button is never an authorization control.
Every lookup first scopes by the active church, so a known object ID from another
church returns `404`.

| Resource or action | Admin | Pastor | Leader | Member |
|---|---|---|---|---|
| People directory API | All people in active church | All people in active church | Active members of groups led/co-led by self | Own linked Person only |
| Person CSV export | Allow | Deny | Deny | Deny |
| Consent read/write | Allow | Allow | Deny | Deny |
| Deactivate Person | Allow | Allow | Allow | Deny |
| Anonymize Person | Allow | Deny | Deny | Deny |
| Hard-delete Person | Allow with approved reason | Deny | Deny | Deny |
| Groups | All in active church | All in active church | Joined groups only | Joined groups only |
| Follow-ups | All in active church | All in active church | Assigned to self only | None |
| Non-confidential care | All in active church | All in active church | Assigned to self only | None |
| Confidential care | All in active church | All in active church | None | None |

“Joined group” means an active `GroupMembership` linked to the Person on the
worker's active `ChurchMembership`. It applies whether the person is a group
leader, co-leader or member. Group-specific mutation rules may narrow this
further when that API is implemented.

`notes` is a general staff field and is absent from member self-service
responses. `faith_background` and `discipleship_stage` are absent unless the
active role is pastor or admin.

Confidential care cases are excluded from unauthorized querysets entirely.
Their title, details and existence must therefore be absent from API responses,
not returned with fields masked by the frontend. The same rule applies to
cross-church records.

CSV is a separate, higher-risk permission boundary from an ordinary API
response. Only church admins may export person data. Every export records the
actor, church, record count and format in the audit log, never the exported
values.

The executable contract lives in
`backend/tests/test_permission_matrix.py`. CI runs that suite explicitly and
also runs the complete backend suite on every pull request.
