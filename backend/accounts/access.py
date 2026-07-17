from django.db.models import QuerySet

from .models import ChurchMembership

ALL_CHURCH_RECORD_ROLES = frozenset(
    {
        ChurchMembership.Role.ADMIN,
        ChurchMembership.Role.PASTOR,
    }
)


def people_visible_to(queryset: QuerySet, membership: ChurchMembership) -> QuerySet:
    """Scope directory records to the active church and role."""
    scoped = queryset.for_church(membership.church)
    if membership.role in ALL_CHURCH_RECORD_ROLES:
        return scoped
    if (
        membership.role == ChurchMembership.Role.LEADER
        and membership.person_id is not None
    ):
        return scoped.filter(
            group_memberships__left_at__isnull=True,
            group_memberships__group__is_active=True,
            group_memberships__group__memberships__person_id=membership.person_id,
            group_memberships__group__memberships__left_at__isnull=True,
            group_memberships__group__memberships__role__in=("leader", "co_leader"),
        ).distinct()
    if membership.person_id is not None:
        return scoped.filter(pk=membership.person_id)
    return scoped.none()


def groups_visible_to(queryset: QuerySet, membership: ChurchMembership) -> QuerySet:
    """Show all groups to senior staff and only joined groups to other roles."""
    scoped = queryset.for_church(membership.church)
    if membership.role in ALL_CHURCH_RECORD_ROLES:
        return scoped
    if membership.person_id is None:
        return scoped.none()
    return scoped.filter(
        memberships__person_id=membership.person_id,
        memberships__left_at__isnull=True,
    ).distinct()


def follow_ups_visible_to(
    queryset: QuerySet,
    membership: ChurchMembership,
) -> QuerySet:
    """Show all follow-ups to senior staff and assigned work to leaders."""
    scoped = queryset.for_church(membership.church)
    if membership.role in ALL_CHURCH_RECORD_ROLES:
        return scoped
    if membership.role == ChurchMembership.Role.LEADER:
        return scoped.filter(assigned_to_id=membership.user_id)
    return scoped.none()


def care_cases_visible_to(
    queryset: QuerySet,
    membership: ChurchMembership,
) -> QuerySet:
    """Keep confidential care with pastors/admins; leaders see assigned open care."""
    scoped = queryset.for_church(membership.church)
    if membership.role in ALL_CHURCH_RECORD_ROLES:
        return scoped
    if membership.role == ChurchMembership.Role.LEADER:
        return scoped.filter(
            assigned_to_id=membership.user_id,
            is_confidential=False,
        )
    return scoped.none()


def can_export_person_data(membership: ChurchMembership) -> bool:
    """Treat bulk extraction as an admin-only operation."""
    return membership.role == ChurchMembership.Role.ADMIN
