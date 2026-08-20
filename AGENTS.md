# Unity agent instructions

Before planning or changing this repository, read
[`PROJECT_HANDOFF.md`](PROJECT_HANDOFF.md). It is the current operational source
of truth for branch rules, product state, safety constraints, open work, testing,
deployment, and the Team Lead workflow. Read linked specialist documents only
when the task enters that area; do not reconstruct the project from chat history.

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
- When multi-agent work is allowed, keep implementation and final review
  independent. The implementing agent must not be the only reviewer.

## Subagent model routing

- `gpt-5.6-luna`: documentation research, mechanical edits, test additions, log
  summaries, code mapping, and simple bounded checks.
- `gpt-5.6-terra`: ordinary feature implementation and medium-complexity work.
- `gpt-5.6-sol`: architecture, authorization/privacy, concurrency, migrations,
  complex debugging, and final independent review.

Use the lowest-cost model that is appropriate for the risk. A task involving
tenant isolation, lifecycle state, sensitive data, concurrency, or migrations is
not a Luna task even if the patch appears small.
