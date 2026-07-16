# ADR 0001: Separate authentication from church and person records

- Status: accepted
- Date: 2026-07-16
- Issue: [#26](https://github.com/jerex763/unity/issues/26)

## Context

Unity needs a stable Django authentication model before its first production
migration. A login may have access to more than one church with a different role
in each, while most people in the directory will never log in. Authentication,
tenant access and pastoral data therefore have different lifecycles.

## Decision

- Use a minimal custom `accounts.User` based on Django's `AbstractUser` from the
  first migration. Do not add church, role or pastoral fields to it.
- Store tenant access in `ChurchMembership`, with `user`, `church`, `role` and
  `is_active`. A partial unique constraint permits history while allowing at most
  one active membership for a user and church.
- Treat `Church` as the tenant root in a small `tenancy` app.
- Keep `Person` independent of authentication. When #2 adds `Person`, it may add
  an optional one-to-one link to `ChurchMembership`; no login is required for a
  person record, and the link must be within the same church.
- Use active membership checks as the minimum authorization boundary. Request
  church selection, queryset scoping and endpoint permissions remain in #5 and
  #31.

## Consequences

- A user can hold different roles in different churches without duplicating
  credentials.
- Deactivating church access does not deactivate the global login or delete
  membership history.
- Role checks must always include the church context; a global `user.role` does
  not exist.
- Changing `AUTH_USER_MODEL` later is avoided.
- The future Person link needs validation that both records belong to the same
  church.

## Alternatives considered

- **Role and church fields on User:** rejected because it assumes one church and
  one role per login.
- **Person as the authentication model:** rejected because most people do not
  need credentials and pastoral records should not share the login lifecycle.
- **Django's default User plus a profile:** rejected because replacing it after
  production migrations is risky and provides no benefit at this stage.
