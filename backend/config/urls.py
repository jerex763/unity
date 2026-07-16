"""Root URL configuration for Unity."""

from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import path
from django.views.decorators.http import require_GET


@require_GET
def health_check(_request: HttpRequest) -> JsonResponse:
    """Return a lightweight process health response."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
]
