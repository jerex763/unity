# Frontend reliability and task-flow delivery — 2026-09-07

## Authorization and decisions

The user chose “reliability → task reorganization → visual convergence”,
explicitly delegated product/design choices to the Team Lead, and said new human
testing is not practical now. This authorizes the scoped local implementation;
it does not authorize push/deploy, live accounts/data, cleanup, or changes to main.

The Team Lead selected a conservative implementation of that direction:

- Repair Profile/registration failure recovery and check-in pending behavior.
- Give phone follow-up selection a focused detail view and explicit return;
  retain desktop master/detail. Home links identify the chosen task.
- Give phone registration rosters a focused view with event context,
  loading/error/retry and return. Preserve desktop inline roster behavior.
- Keep Directory filters/search only in the current session's memory; preserve
  return context without placing name/contact searches in URLs or storage.
- Keep all contact channels accessible through a directory disclosure; make
  read-only values fully readable and retain clipboard fallback.
- Retain the palette, typeface, desktop sidebar, API/permissions and whole-profile
  editing model. Section-level partial edits and identity-model changes are out
  of scope. Reduce operational heading scale and make filters discoverable.

The pre-implementation local mock is
`docs/ui-mockups/task-flow-2026-09-07.html`: 9 states × 5 widths, checked for
horizontal overflow, with representative mobile/desktop previews inspected.
The user’s express delegation is the authority for Team Lead design selection;
no new human visual approval or human acceptance is claimed.

## Model routing

GPT-5.6 Sol implementation agents own separate loading/recovery, check-in pending,
and task-navigation areas. The main GPT-6 task owns scope, integration, directory
state/contact layout, and release judgment. A separate Sol review is required;
implementers are not their own final reviewer. Spark is not exposed in the
current sub-agent model list and was not used. Even if exposed, stale async
results and navigation state are outside the project's Spark fast lane.

This choice uses the project’s model routing and the available runtime. Official
[model comparison](https://developers.openai.com/api/docs/models/compare)
positions GPT-6 Astra for the hardest end-to-end work and Sol for complex
professional work. This is not a measured Unity-specific quality/cost benchmark,
nor a claim about the user's subscription billing.

## Acceptance criteria

1. Simulated failed Profile/detail requests exit loading and transient failure
   can retry; inaccessible IDs remain neutral and do not show another person.
2. Previous async requests cannot replace a newly selected person/event/task.
3. Check-in double submission sends one request per record, unrelated rows remain
   usable, and failures release pending state. Walk-in failure retains fields.
4. Directory/profile contact text is readable without internal clipping at
   320/375/390/430 and desktop; original copy/WhatsApp/email handoffs still work.
5. Phone task/roster selection reveals the selected content in the viewport;
   return preserves context. Direct task links do not silently select another ID.
6. Keyboard focus, modal Escape/trapping, and route/viewport transitions remain
   usable. New visual states use existing styling and accessible status semantics.
7. Formatting, lint, unit tests, build, browser tests and independent review pass.

## Limits

Automated and simulated browser evidence replaces neither real worker acceptance
nor the outstanding controlled-pilot release gate. Real mobile keyboards/Safari,
actual operation frequency and field-use hypotheses remain unverified. No new
claim of production readiness should be made from this delivery alone.

## Delivery evidence

Completed, committed at `47fcdcc`, and pushed/deployed after the user's separate
explicit authorizations. No PR, GitHub issue update, live account/data write or
cleanup was performed.

- CI run `34114621918` passed all four jobs for `47fcdcc`.
- Render deployment `dep-daf9kr95efls73aja2o0` / GitHub deployment `6307308121`
  succeeded at `2026-09-07T11:06:34Z`.
- Live health returned 200/ok; home, People and task deep-link SPA routes and
  admin CSS returned 200, while an unknown API path returned 404.
- Live JS/CSS bytes match the tested local build, including Back controls,
  directory contact disclosure and focused mobile-detail feature signals.
  These are unauthenticated delivery probes, not a new worker acceptance run.

- Formatting, ESLint, 9 Vitest files / 121 tests, TypeScript and production build
  passed after the final code correction.
- Full Playwright suite: **65/65 passed**, covering 320, 375, 390, 430 and desktop.
  It covers contact disclosure/readability/copy fallback, directory search and
  scroll/focus return, exact task links, per-task drafts, roster retry, modal
  behavior, event-day workflows and existing public-registration flows.
- Unit regressions cover delayed/failed/stale loads, duplicate pending check-ins,
  independent rows, route changes and failed/revisited walk-ins.
- Independent Sol reviewer returned **ACCEPT** after a cross-event check-in race
  was corrected. The final mobile scroll correction was separately accepted:
  Back and heading now both clear the sticky topbar.
- Actual fictional-data browser captures are in
  [`ui-delivery-2026-09-07/`](ui-delivery-2026-09-07/), with numeric layout evidence
  in `layout-evidence.json`. All 12 captures at 320/390/1280 have no horizontal
  page overflow or measured contact clipping. Representative mobile Profile,
  Directory, roster, task and desktop task screenshots were visually inspected.
  Directory collapsed rows in this fixture are about 180px on mobile, compared
  with about 486px for the previous expanded four-channel audit fixture; this is
  layout evidence, not a measured productivity gain.
- Final local build assets: `index-B-FR7G0t.js` and `index-C-EEBaEX.css`.

The first integration browser run was invalidated by a shared development-server
shutdown and also exposed old test selectors matching the now-hidden queue.
Selectors were scoped to the active detail, then the complete suite passed on a
root-owned server. No assertions were removed to hide an application failure.

## Next decision and remaining uncertainty

The implemented order remains the recommendation because observed failure modes
had stronger evidence than a wholesale visual redesign. Contact disclosure and
phone focused detail are design choices supported by layout/navigation tests;
their effect on real task speed is still a hypothesis. If workers predominantly
contact people directly from the directory, reconsider the collapsed default.
If desktop usage dominates, prioritize its task density over further phone
layout work. Do not infer either usage pattern from this synthetic test run.

No new human session is requested now. Push, CI and deployment verification are complete; the controlled-pilot
gate #32 remains open. A future real-device check should focus
on Safari, mobile keyboard behavior and actual contact/return task completion.
Optional deferred accessibility work: complete the pre-existing Profile tablist,
tabpanel associations and arrow-key behavior. Section-level profile editing and
wholesale navigation replacement remain unapproved, unimplemented proposals.
