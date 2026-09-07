# Release gap review — 2026-09-07

## Verified baseline

- Local HEAD and fetched `origin/codex/mvp-next`: `327d3d5`, no divergence.
- CI `34114978337`: success. Render GitHub deployment `6307378878`:
  success at `2026-09-07T11:10:49Z`. Application changes remain `47fcdcc`.
- Pre-existing local edits to AGENTS.md and PROJECT_HANDOFF.md are preserved.
  No code, remote issue, infrastructure, data, account or schedule was changed.

## Evidence and disposition

| Item | Confirmed evidence | Remaining work | Disposition |
|---|---|---|---|
| [#109](https://github.com/jerex763/unity/issues/109) | Open, no comments. Implementation and acceptance evidence in handoff; controlled worker feedback in pilot review. | Publish the existing implementation/test/worker evidence before closure. | Primarily record reconciliation; do not reimplement. |
| [#110](https://github.com/jerex763/unity/issues/110) | Open parent; its sole comment covers Batch 1. Mobile task/roster and compact directory changes subsequently deployed at 47fcdcc. | Record later delivery; distinguish delivered scope from search suggestions, active-link wording and shared primitives still deferred. | Keep parent open; do not treat every later design idea as a release blocker. |
| [#32](https://github.com/jerex763/unity/issues/32) | Open. Issue comments stop at worker preparation; repository review records three actual workers completing fictional-data tasks on 2026-08-28. | Reconcile existing feedback, activity-specific permission/audit review, isolated restore, ownership and cleanup evidence. | Release gate remains open. Missing device/time fields must not be invented. |
| [#99](https://github.com/jerex763/unity/issues/99) | Open. Workflow remains manual-only. Latest three runs all failed; no newer backup workflow run found. | Fix tool setup and configuration preflight, then validate infrastructure and a selected backup/restore path. | Highest-priority bounded engineering task. |

## Backup: facts versus unknowns

The latest backup run `29694284982` failed both Install backup tools and Alert
on failure. Current backup.yml still installs awscli through apt on ubuntu-latest;
Issue #99 records this as the Ubuntu 24.04 installation failure. The scheduled
trigger is correctly paused. The shared backup.sh checks three required values,
but only after installation, and does not preflight the full S3/alert setup.

CI restoration uses a temporary age key and two fictional PostgreSQL probe rows,
with a local file destination. It proves that that encryption/restore path works;
it does not test the configured deployment database, private S3 storage, retained
recovery key or actual alert delivery.

Both environment-secret and repository-secret metadata reads returned HTTP 403.
Therefore current secret configuration is **unknown**, not confirmed absent.
The old Issue's missing-secret statement is historical. No secret values were
requested, displayed or written. Object privacy, retention, identity permissions,
key custody and actual recovery duration remain unverified. No successful run in
this workflow is not proof that no external/manual backup exists.

## Chosen next task

Prepare a local repair for #99's workflow prerequisites, leaving cron paused:

1. Use an Ubuntu-compatible AWS CLI installation/verification path.
2. Add an early preflight for all required backup configuration, reporting only
   missing variable names, never values, before dependency installation or dump.
3. Test missing/complete configuration and tool failures with fake values and
   stubbed commands; retain existing isolated encryption/restore CI coverage.
4. Obtain independent review of failure handling and secret-safe output.

Acceptance: absent configuration fails clearly before any database/network
backup action; complete fake configuration proceeds; installation is verified;
no secrets are printed; no schedule, live data or infrastructure is changed.
This is a prerequisite repair, not completion of #99 or evidence of a usable
operational backup. Before selecting the installation method, verify current
runner/AWS documentation. No real backup run is required for this local task.

Afterward, infrastructure configuration and an isolated operational restore need
concrete source/target/key/storage details and the documented authorization.
Do not request credentials in chat. Do not trigger the failure-alert test during
this audit, since it sends a message to an external channel.

## Decision boundaries

For ongoing pilot use, recovery readiness outranks additional UI polish. For a
short-lived fictional demo, retain the paused schedule and avoid provisioning
paid infrastructure solely to close a checkbox. If a concrete access or data-loss
incident is found, that supersedes this order.

Human testing is deferred as requested. Existing feedback can be reconciled
without asking workers to repeat it. A future move to real data is a separate
product/privacy decision: the older Issue #32 real-activity wording does not
override the current fictional-only environment rule.

## Local prerequisite delivery

Following explicit approval to start, the bounded #99 repair is implemented in
backup.yml, install_tools.sh and check_production_config.sh. Nine offline unittest
groups pass, using isolated PATH stubs and fictional configuration only. The main
agent separately reviewed implementation and reran all tests; no material blocker
was found. CI runs the new suite in addition to existing restore coverage.

The actual GitHub runner installation and operational restore were not executed
locally; existing CI restore success is historical evidence, not a test of this
unpublished patch. Cron remains paused. No commits, pushes, infrastructure writes,
database actions, alert messages or GitHub issue edits were performed.

The user's public-link question was checked against EventsPage and backend event
services: Show/Copy remains available in the current page's in-memory state;
after refresh/navigation the raw token cannot be recovered from its stored SHA-256
digest. Previously sent/saved URLs or history from opening the URL may recover
it. Replacing the link invalidates the old URL. No public-link implementation or
live token was changed; recoverable link storage needs a separate design decision.

## Commit reconciliation

The user subsequently authorized a local commit of the verified backup
prerequisites and public-link recovery implementation. Earlier no-commit and
design-only statements above describe those review stages; current local
implementation/test evidence is in public-link-recovery-design.md and the
handoff. No new push, deployment or operational backup was performed.
