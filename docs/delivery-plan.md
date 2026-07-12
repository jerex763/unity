# Delivery Plan — how the team remembers what comes next

This document is the team's external memory. A smaller first release does **not** delete the larger vision. It separates the destination from the work currently in progress.

## The three layers

1. **Vision** — the full church CRM + AI direction remains in [roadmap.md](roadmap.md).
2. **Backlog** — Issues preserve future ideas, decisions and research so the team does not rely on memory.
3. **Current milestone** — only the small set the team is actively delivering.

When a milestone finishes, review real usage, then promote the next Issues from the backlog. Do not start everything at once.

## Priority vocabulary

Use these labels when the label set is added:

- `now` — required for the current milestone
- `next` — likely next after the current milestone
- `later` — preserved future work, not forgotten
- `needs-research` — outcome or design is not clear enough to build
- `privacy-sensitive` — handles pastoral, religious, family, child or care data
- `ai` — AI-assisted feature requiring evaluation and human review

Milestones show delivery order. Labels show urgency and risk. Issues contain acceptance criteria.

## Delivery sequence

### M0 — Safe foundation

Build the shared foundation before real member data enters Unity:

- Django, Postgres and frontend scaffolds
- Minimal custom User plus ChurchMembership decision ([#26](https://github.com/jerex763/unity/issues/26))
- Models, migrations and Django Admin
- Authentication, role permissions and church scoping
- Audit log for sensitive/destructive actions ([#27](https://github.com/jerex763/unity/issues/27))
- Consent and privacy-notice version record ([#28](https://github.com/jerex763/unity/issues/28))
- Automated backups and a tested restore runbook ([#29](https://github.com/jerex763/unity/issues/29))
- Safe deactivate/anonymize/delete behaviour ([#30](https://github.com/jerex763/unity/issues/30))
- Permission and privacy test matrix ([#31](https://github.com/jerex763/unity/issues/31))
- CI on every PR
- Fictional test data only

**Exit gate:** cross-church access is denied; confidential records are role-gated; critical actions are audited; backup restoration has been tested.

### M1 — Usable people directory

- Person and household records
- Mobile directory, search and filters
- Person profile
- Relationships and invited-by
- CSV import with validation and duplicate review

**Exit gate:** an authorized worker can import fictional/sample records, find a person on a phone, and cannot see fields outside their role.

### M2 — Event loop

- Event create/edit
- Registration and cancellation
- Transport need and leader list
- Manual check-in ([#33](https://github.com/jerex763/unity/issues/33))
- Walk-in quick-add

QR check-in stays in the backlog until the manual flow has been used successfully.

**Exit gate:** one real-shaped event can move from signup to attendance without WhatsApp list editing.

### M3 — Newcomer follow-up loop

- First visit creates one open follow-up
- Assignment and due date
- Interaction log
- My follow-ups dashboard
- Close with an outcome

**Exit gate:** a walk-in can move from attendance to assigned follow-up and a recorded outcome without being lost.

### Pilot release — learn before adding modules ([#32](https://github.com/jerex763/unity/issues/32))

- Test with fictional data first
- Run one small church activity
- Ask 2–3 actual workers to use it on their phones
- Fix permission, workflow and usability failures
- Perform a backup restore
- Write a short pilot review: what worked, what failed, what should be next

### Next / later

Choose after the pilot rather than by guesswork:

- QR check-in
- Groups and memberships
- Care/prayer workflow
- Member self-service
- Communications
- Analytics
- Localization
- AI assistance

The full module list and permanent cuts remain in [roadmap.md](roadmap.md).

## AI release order

AI begins only after permission boundaries and reliable operational data exist.

1. Duplicate-person suggestions
2. Draft summaries of interaction notes
3. Natural-language directory search translated into permission-safe filters
4. Draft follow-up messages that a human reviews and sends
5. Explained next-step suggestions with evidence, confidence and accept/reject feedback

AI must not autonomously assess spiritual maturity, scan private messages, send sensitive messages, or make pastoral decisions. "AI is not the pastor; it is the assistant." Every AI feature needs:

- the minimum necessary data
- human review
- an explanation
- auditability
- evaluation with fictional/redacted examples
- a safe fallback when the model is unavailable

## Weekly project routine

1. Review the current milestone.
2. Each person claims one unassigned Issue.
3. Open a small PR linked with `Closes #N`.
4. Another person reviews it.
5. Merge only when CI and the definition of done pass.
6. At milestone end, demonstrate the workflow and choose the next Issues.

If nobody remembers what comes next, read this document, the current milestone and the `next` backlog. The plan belongs in GitHub, not in one person's memory.
