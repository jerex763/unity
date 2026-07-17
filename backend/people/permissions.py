from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from accounts.permissions import ROLE_CAPABILITIES, Capability


class HasPersonDirectoryAccess(BasePermission):
    """Allow self-service reads, but require ministry capability for writes."""

    message = "The active church role does not allow this directory action."

    def has_permission(self, request: Request, view: object) -> bool:
        membership = getattr(request, "church_membership", None)
        if membership is None:
            return False
        if request.method in SAFE_METHODS:
            return True
        return Capability.LEAD_MINISTRY in ROLE_CAPABILITIES.get(
            membership.role,
            frozenset(),
        )
