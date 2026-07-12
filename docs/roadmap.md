# Roadmap — full vision vs. current scope

The requirement docs (Google Drive: functional requirements, UI requirements, DB model sheet) describe a 13-module product with an official 5-phase plan. This file maps that full vision to what we're building now, so nobody mistakes the MVP for the destination — or the destination for the MVP.

This file preserves the destination. For the current delivery order, release gates and weekly team routine, see [delivery-plan.md](delivery-plan.md).

## Requirements-doc phases ↔ our milestones

| Docs phase | Docs scope | Our milestone(s) |
|---|---|---|
| Phase 1 | Core membership + attendance | M0 Foundation, M1 People Directory |
| Phase 2 | Events + Groups | M2 Events & Check-in, M4 Groups (part) |
| Phase 3 | Follow-Up + Unity Assistant | M3 Follow-up Queue (Assistant deferred) |
| Phase 4 | Insights dashboard + financial tools | post-MVP |
| Phase 5 | Continuous AI training + localization | post-MVP |

**Parallelism note for the team:** milestone order is priority order, not a strict dependency chain. Finish M0's security and privacy exit gate first. M1 and M2 can then proceed in parallel. M3 depends on M2 (walk-in registration feeds follow-up auto-creation). M4 stays preserved in the backlog until the pilot identifies it as the next priority.

## Module-by-module status

| Module (requirement docs) | Status | Notes |
|---|---|---|
| People & Directory | **MVP — M1** | Advanced filters ✓; natural-language search, engagement prediction, duplicate detection → post-MVP |
| Events & Calendar | **MVP — M2** | CRUD + registration + manual check-in; QR and AI scheduling/turnout prediction → post-pilot |
| Check-In | **MVP — M2** | Manual first; QR and child check-in (guardian verification, allergy badges) → post-pilot; facial recognition → **cut** |
| Follow-Up Queue | **MVP — M3** | Possible/Probable/Likely tiers, staff-assessed; AI rationale chips, guided contact modal, FAITH trait scoring → post-MVP |
| Groups & Ministries | **Backlog — M4** | Preserved, but scheduled after the first pilot; AI participation monitoring → later |
| Care & Prayer | **Backlog — M4** | Preserved, but scheduled after the first pilot; confidential data requires the M0 permission/audit foundation |
| Home Dashboard | post-MVP | M3's "my follow-ups" view covers the highest-value leader card first |
| Member self-service portal | post-MVP | MVP is staff/leader-facing; members interact via leaders until the core is solid |
| Communication Hub | post-MVP | Broadcasts/automations later; **sentiment monitoring of member messages → cut** |
| Giving & Stewardship | post-MVP | External giving links (Tithe.ly/Pushpay) first; never store card data ourselves |
| Unity Assistant (AI co-pilot) | post-MVP | Docs phase 3; start with weekly batch AI suggestions before conversational UI |
| Insights & Analytics | post-MVP | Docs phase 4 |
| Settings & Privacy | **M0 foundation + later UI** | Audit, basic consent record, backup/restore and safe data lifecycle are M0; member-facing controls expand later |
| Onboarding / Consent flow | **M0 record + later self-service** | Store consent source/version in M0; member self-service onboarding ships with the portal |

## Permanently cut (decision record)

| Feature | Why |
|---|---|
| Facial recognition check-in | Biometric data + children involved — legal/ethical liability far exceeds convenience, even with the consent flow the docs propose. QR is enough. |
| Sentiment monitoring of member communications | Scanning private messages erodes the trust the product exists to build. Care needs surface through the follow-up and care workflows instead. |
| Ethnicity/race data collection | No feature needs it; GDPR special-category liability. `faith_background` covers the pastoral use case. |
| In-app payment processing | Financial compliance burden; established giving platforms do it better. |

## Guiding constraints (from the docs, kept)

- Five-stage discipleship framing: Pre-Evangelism → Evangelism → Conversion → Maturity → Leadership (`person.discipleship_stage`)
- "AI is not the pastor; it's the assistant" — every future AI action needs an explanation and human review for sensitive steps
- Warm, pastoral design language — see [design.md](design.md)
- Accessibility: 4.5:1 contrast minimum
- Multilingual-ready: externalize all UI strings from day one (i18next), even though translations come later
