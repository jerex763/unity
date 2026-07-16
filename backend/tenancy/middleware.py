from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from accounts.constants import ACTIVE_CHURCH_SESSION_KEY
from accounts.models import ChurchMembership


class ActiveChurchMiddleware:
    """Resolve and revalidate the session's active church on every request."""

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.church = None
        request.church_membership = None

        if request.user.is_authenticated and request.user.is_active:
            church_id = request.session.get(ACTIVE_CHURCH_SESSION_KEY)
            if isinstance(church_id, int):
                membership = (
                    ChurchMembership.objects.active()
                    .for_user(request.user)
                    .filter(church_id=church_id)
                    .select_related("church", "person")
                    .first()
                )
                if membership is not None:
                    request.church = membership.church
                    request.church_membership = membership
                else:
                    request.session.pop(ACTIVE_CHURCH_SESSION_KEY, None)
            elif church_id is not None:
                request.session.pop(ACTIVE_CHURCH_SESSION_KEY, None)

        return self.get_response(request)
