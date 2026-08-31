from django.http import HttpRequest


class SuperuserOnlyAdminMixin:
    """Restrict project admin models to active superusers."""

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request: HttpRequest) -> bool:
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return request.user.is_active and request.user.is_superuser
