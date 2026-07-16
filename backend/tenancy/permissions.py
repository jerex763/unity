from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from accounts.permissions import ROLE_CAPABILITIES, Capability


class HasActiveChurchMembership(BasePermission):
    message = "An active church membership is required."

    def has_permission(self, request: Request, view: object) -> bool:
        return bool(
            request.user.is_authenticated
            and getattr(request, "church", None) is not None
            and getattr(request, "church_membership", None) is not None
        )


class HasChurchCapability(BasePermission):
    message = "The active church role does not allow this action."

    def has_permission(self, request: Request, view: object) -> bool:
        membership = getattr(request, "church_membership", None)
        capability = getattr(view, "required_capability", None)
        if membership is None or not isinstance(capability, Capability):
            return False
        return capability in ROLE_CAPABILITIES.get(membership.role, frozenset())
