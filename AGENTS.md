# Unity agent instructions

Before planning or changing this repository, read
[`PROJECT_HANDOFF.md`](PROJECT_HANDOFF.md). It is the current operational source
of truth for branch rules, product state, safety constraints, open work, testing,
deployment, and the Team Lead workflow. Read linked specialist documents only
when the task enters that area; do not reconstruct the project from chat history.

Use progressive disclosure: start with these two entry documents, then inspect
only the relevant Issue, specialist documentation, code, tests, and history.
Always verify dynamic Git, GitHub, CI, and deployment facts before relying on a
recorded snapshot. If they disagree, current observed state wins and the handoff
must be corrected.

## Non-negotiable working rules

- Work on `codex/mvp-next`. Do not modify, merge, or push `main` without fresh,
  explicit user authorization.
- Preserve the untracked `output/` directory. Never delete, overwrite, stage, or
  commit it.
- Use fictional data only in the Render/Neon demo. Never place credentials,
  database URLs, secrets, or real church/member data in chat, Git, logs, issues,
  screenshots, fixtures, or documentation.
- Treat push/deploy, test-account creation, test-data creation, and data cleanup
  as separate authorization gates. Do not infer one from another.
- Evaluate product suggestions as a responsible Team Lead. Confirm the workflow,
  permissions, privacy impact, and MVP value; do not implement a suggestion only
  because it was proposed.
- Continue autonomously when the next safe in-scope action is clear. Stop for a
  genuine product choice, real-user/data handling, destructive work, a new
  privacy/security decision, external credentials/accounts, or an authorization
  gate defined here or in the handoff.
- Keep each task to the smallest reliable change. Record adjacent ideas instead
  of silently expanding scope.
- When multi-agent work is allowed, keep implementation and final review
  independent. The implementing agent must not be the only reviewer.
- After feature, release, deployment, acceptance, permission, architecture, or
  other material project work, reconcile `PROJECT_HANDOFF.md` with the resulting
  branch, GitHub, CI/deployment, product decisions, risks, blockers, and next
  priority before ending the work session. Do not create timestamp-only churn
  when no durable state changed.

## Subagent model routing

- `gpt-5.6-luna`: documentation research, mechanical edits, test additions, log
  summaries, code mapping, and simple bounded checks.
- `gpt-5.6-terra`: ordinary feature implementation and medium-complexity work.
- `gpt-5.6-sol`: architecture, authorization/privacy, concurrency, migrations,
  complex debugging, and final independent review.

Use the lowest-cost model that is appropriate for the risk. A task involving
tenant isolation, lifecycle state, sensitive data, concurrency, or migrations is
not a Luna task even if the patch appears small.
