# Roadmap — full vision vs. current scope

The requirement docs (Google Drive: functional requirements, UI requirements, DB model sheet) describe a 13-module product with an official 5-phase plan. This file maps that full vision to what we're building now, so nobody mistakes the MVP for the destination — or the destination for the MVP.

## Requirements-doc phases ↔ our milestones

| Docs phase | Docs scope | Our milestone(s) |
|---|---|---|
| Phase 1 | Core membership + attendance | M0 Foundation, M1 People Directory |
| Phase 2 | Events + Groups | M2 Events & Check-in, M4 Groups (part) |
| Phase 3 | Follow-Up + Unity Assistant | M3 Follow-up Queue (Assistant deferred) |
| Phase 4 | Insights dashboard + financial tools | post-MVP |
| Phase 5 | Continuous AI training + localization | post-MVP |

**Parallelism note for the team:** milestone order is priority order, not a strict dependency chain. After M0 lands, M1 / M2 / M4 can proceed in parallel. M3 depends on M2 (walk-in registration feeds follow-up auto-creation).

## Module-by-module status

| Module (requirement docs) | Status | Notes |
|---|---|---|
| People & Directory | **MVP — M1** | Advanced filters ✓; natural-language search, engagement prediction, duplicate detection → post-MVP |
| Events & Calendar | **MVP — M2** | CRUD + registration + QR check-in; AI scheduling/turnout prediction → post-MVP |
| Check-In | **MVP — M2** | QR + manual; child check-in (guardian verification, allergy badges) → post-MVP; facial recognition → **cut** |
| Follow-Up Queue | **MVP — M3** | Possible/Probable/Likely tiers, staff-assessed; AI rationale chips, guided contact modal, FAITH trait scoring → post-MVP |
| Groups & Ministries | **MVP — M4** | CRUD, membership, health status; AI participation monitoring → post-MVP |
| Care & Prayer | **MVP — M4** | Kanban + urgency + confidential gating; anonymous prayer, "I prayed" counter, AI theme tagging → post-MVP |
| Home Dashboard | post-MVP | M3's "my follow-ups" view covers the highest-value leader card first |
| Member self-service portal | post-MVP | MVP is staff/leader-facing; members interact via leaders until the core is solid |
| Communication Hub | post-MVP | Broadcasts/automations later; **sentiment monitoring of member messages → cut** |
| Giving & Stewardship | post-MVP | External giving links (Tithe.ly/Pushpay) first; never store card data ourselves |
| Unity Assistant (AI co-pilot) | post-MVP | Docs phase 3; start with weekly batch AI suggestions before conversational UI |
| Insights & Analytics | post-MVP | Docs phase 4 |
| Settings & Privacy (consent toggles, data export/delete) | post-MVP | Required before any member-facing launch |
| Onboarding / Consent flow | post-MVP | Ships with member portal |

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
