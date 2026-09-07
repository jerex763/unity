# Issue #109 acceptance review — 2026-09-08

Reviewed application code at `31a23b6` (documentation-only successor to deployed
`09c2a41`). No application changes or live data writes were needed.

## Acceptance mapping

| Requirement | Current evidence |
|---|---|
| Separate directory writes from check-in | `accounts/permissions.py` defines distinct `WRITE_PERSON_DIRECTORY` and `EVENT_CHECK_IN`; People and event endpoints enforce them independently. |
| Admin/Pastor writes; Leader/Member denied | `test_person_api.py::test_directory_write_capability_covers_profiles_and_relationships` checks all four roles, profiles and relationships, and denied-write nonmutation. |
| Admin/Pastor/Leader check-in; Member denied | `test_checkin_person_api.py::test_check_in_capability_covers_search_walk_in_and_manual_check_in` checks all four roles on all three entry points. |
| Minimal search, duplicate names, tenant isolation | `test_check_in_search_is_minimal_masked_and_church_scoped` asserts exact response keys, masked contacts, distinct duplicate-name records and exclusion of other churches/inactive people. |
| Explicit selected person, preserve profile and registration | `test_selected_person_check_in_status_and_profile_nonmutation` checks all five initial registration states, unchanged contact/profile fields and preserved active-registration note/time. Cancelled entries become walk-ins and clear the cancellation digest. |
| Selected person cannot cross churches | `test_selected_person_cannot_cross_church` expects 404 and no registration creation. Manual-check-in and new-visitor tests additionally cover cross-church event/registration IDs. |
| New visitor needs contact, never name-only auto-match | `test_walk_in_api.py` covers missing contact, name-only nonmatching, same-church contact reuse, conflicting contacts and inactive lifecycle records. |
| Visitor-only follow-up triggered by attendance | `test_selected_existing_person_preserves_visitor_only_first_visit_follow_up` verifies one visitor task across two events and no member task; `test_pilot_flow.py` covers the broader flow. |
| Two clear frontend paths | `frontend/e2e/events-interactions.spec.ts`, test `event-day check-in is separate, searchable, and supports walk-ins`, asserts Existing person/New visitor controls, duplicate-name choices, selection clearing, payloads and keyboard modal behavior. Existing multi-viewport evidence is recorded in the delivery documents; no fresh browser run is claimed here. |

## Fresh local verification

Ran with `TEST_DATABASE_URL` explicitly unset and
`DJANGO_SETTINGS_MODULE=config.settings.test`, using SQLite in memory:

```text
tests/test_checkin_person_api.py
tests/test_walk_in_api.py
tests/test_manual_checkin_api.py
tests/test_person_api.py
tests/test_person_lifecycle.py
tests/test_permission_matrix.py
tests/test_pilot_flow.py
98 passed (159 warnings), 1.52 seconds
```

Frontend targeted run: `npm test -- --run src/events/EventCheckInPage.test.tsx`:
**6 passed**. Includes pending submission guards, failed walk-in field retention
and event-route state isolation.

These tests do not establish PostgreSQL row-lock behavior or human mobile usability.
No new row-lock claim is made; previous PostgreSQL verification remains separately
recorded. Warnings were reported by pytest, not treated as a clean warning audit.

## Historical finding and decision

The old #32 comment about Leader deactivating unrelated same-church people no
longer describes current code: `PersonDeactivateView` filters through
`people_visible_to` before locking the target. The fresh lifecycle regression
expects 404 for unrelated and cross-church targets, unchanged status and no
deactivation audit entry; it passed.

No acceptance blocker was found in this bounded review. #109 is ready for its
implementation, automated and existing worker evidence to be published and closure
considered; no GitHub comment or closure was performed. The worker's general
completion report is not evidence that every edge case was manually exercised.
#32 remains open; Leader's broader event-operator role remains intentional current
policy, not a newly restricted role. Do not reopen paid backup setup or add new
modules merely because this review found no required code fix.
