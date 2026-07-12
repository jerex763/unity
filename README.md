# Unity

Church membership + discipleship management app. Internal tool first; productization later.

**MVP scope (three pillars):**
1. People directory — members, visitors, relationships
2. Newcomer follow-up queue — simplified FAITH matrix pipeline
3. Events — registration (replacing WhatsApp numbered-list signups) + QR check-in

**Stack:** Django + Postgres backend, React responsive PWA frontend.

## Docs

- [Database model v1](docs/db-model.md) — 11 entities, Django-ready
- Requirements live in Google Drive (Unity DB model sheet, UI requirements notes, functional requirement notes)

## Status

- [x] Requirements gathered
- [x] DB model v1
- [ ] Django project scaffold + models + admin
- [ ] API (DRF)
- [ ] React PWA

## Principles

- Every domain table carries `church_id` from day one (cheap multi-tenant insurance)
- Sensitive data minimized: no ethnicity collection, suburb not street address, pastoral notes role-gated
- No payments in-app; no facial recognition; no message sentiment analysis
