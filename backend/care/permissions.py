from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from accounts.models import ChurchMembership


class HasFollowUpAccess(BasePermission):
    message = "The active church role does not allow follow-up access."

    def has_permission(self, request: Request, view: object) -> bool:
        membership = getattr(request, "church_membership", None)
        return (
            membership is not None and membership.role != ChurchMembership.Role.MEMBER
        )
