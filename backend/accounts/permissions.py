from enum import StrEnum

from tenancy.models import Church

from .models import ChurchMembership, User


class Capability(StrEnum):
    MANAGE_CHURCH = "manage_church"
    MANAGE_DESTRUCTIVE = "manage_destructive"
    MANAGE_PERSON_CONSENT = "manage_person_consent"
    VIEW_SENSITIVE_PERSON = "view_sensitive_person"
    VIEW_CONFIDENTIAL_CARE = "view_confidential_care"
    LEAD_MINISTRY = "lead_ministry"
    SELF_SERVICE = "self_service"


ROLE_CAPABILITIES: dict[str, frozenset[Capability]] = {
    ChurchMembership.Role.ADMIN: frozenset(Capability),
    ChurchMembership.Role.PASTOR: frozenset(
        {
            Capability.VIEW_SENSITIVE_PERSON,
            Capability.VIEW_CONFIDENTIAL_CARE,
            Capability.LEAD_MINISTRY,
            Capability.MANAGE_PERSON_CONSENT,
            Capability.SELF_SERVICE,
        }
    ),
    ChurchMembership.Role.LEADER: frozenset(
        {
            Capability.LEAD_MINISTRY,
            Capability.SELF_SERVICE,
        }
    ),
    ChurchMembership.Role.MEMBER: frozenset({Capability.SELF_SERVICE}),
}


def get_active_membership(
    user: User,
    church: Church,
) -> ChurchMembership | None:
    """Return active church access for an active user."""
    if not user.is_active:
        return None
    return (
        ChurchMembership.objects.active()
        .for_user(user)
        .for_church(church)
        .select_related("church", "person")
        .first()
    )


def has_church_role(user: User, church: Church, roles: set[str]) -> bool:
    membership = get_active_membership(user, church)
    return membership is not None and membership.role in roles


def has_capability(user: User, church: Church, capability: Capability) -> bool:
    membership = get_active_membership(user, church)
    if membership is None:
        return False
    return capability in ROLE_CAPABILITIES.get(membership.role, frozenset())
