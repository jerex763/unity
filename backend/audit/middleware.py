from collections.abc import Callable
from uuid import uuid4

from django.http import HttpRequest, HttpResponse

from .context import AuditContext, bind_audit_context


class AuditRequestMiddleware:
    """Attach one server-generated request ID and actor context to each request."""

    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse],
    ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = uuid4()
        request.audit_request_id = request_id
        actor_id = request.user.pk if request.user.is_authenticated else None

        with bind_audit_context(AuditContext(actor_id=actor_id, request_id=request_id)):
            response = self.get_response(request)

        response["X-Request-ID"] = str(request_id)
        return response
