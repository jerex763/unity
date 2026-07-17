from django.contrib import admin
from django.http import HttpRequest

from config.admin import SuperuserOnlyAdminMixin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "church",
        "actor",
        "target_type",
        "target_id",
        "request_id",
    )
    list_filter = ("church", "actor", "action", "created_at")
    search_fields = (
        "request_id",
        "target_type",
        "target_id",
        "actor__username",
        "church__name",
    )
    list_select_related = ("church", "actor")
    date_hierarchy = "created_at"
    readonly_fields = (
        "created_at",
        "action",
        "church",
        "actor",
        "target_type",
        "target_id",
        "request_id",
        "metadata",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return False
