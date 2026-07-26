"""Root URL configuration for Unity."""

from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404, HttpRequest, JsonResponse
from django.urls import include, path, re_path
from django.views.decorators.http import require_GET

admin.site.site_header = "Unity administration"
admin.site.site_title = "Unity admin"
admin.site.index_title = "Church operations"


@require_GET
def health_check(_request: HttpRequest) -> JsonResponse:
    """Return a lightweight process health response."""
    return JsonResponse({"status": "ok"})


@require_GET
def frontend_index(_request: HttpRequest) -> FileResponse:
    """Serve the built React entry point for client-side routes."""
    index_path = Path(settings.FRONTEND_DIST_DIR) / "index.html"
    if not index_path.is_file():
        raise Http404("Frontend build is not available")
    return FileResponse(index_path.open("rb"), content_type="text/html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/people/", include("people.urls")),
    path("api/events/", include("events.urls")),
    path("api/follow-ups/", include("care.urls")),
    path("api/health/", health_check, name="health-check"),
    re_path(
        r"^(?!(?:api|admin|static|assets)(?:/|$)).*$",
        frontend_index,
        name="frontend-index",
    ),
]
