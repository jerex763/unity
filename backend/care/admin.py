from django.contrib import admin
from django.http import HttpRequest

from audit.models import AuditEvent
from audit.services import record_audit_event
from config.admin import SuperuserOnlyAdminMixin

from .models import CareCase, FollowUp, FollowUpDueDateChange, Interaction


@admin.register(FollowUp)
class FollowUpAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "person",
        "status",
        "engagement",
        "assigned_to",
        "due_at",
        "church",
    )
    list_filter = ("church", "status", "engagement", "source", "due_at")
    search_fields = ("person__full_name", "outcome", "assigned_to__username")
    autocomplete_fields = ("person", "assigned_to")
    list_select_related = ("church", "person", "assigned_to")
    readonly_fields = (
        "church",
        "person",
        "source",
        "engagement",
        "status",
        "assigned_to",
        "due_at",
        "due_schedule_changed_at",
        "status_changed_at",
        "closed_at",
        "outcome",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: FollowUp | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: FollowUp | None = None,
    ) -> bool:
        return False


@admin.register(FollowUpDueDateChange)
class FollowUpDueDateChangeAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "follow_up",
        "previous_due_at",
        "new_due_at",
        "reason",
        "actor",
        "created_at",
        "church",
    )
    list_filter = ("church", "reason", "created_at")
    list_select_related = ("church", "follow_up", "actor", "interaction")
    readonly_fields = (
        "follow_up",
        "church",
        "previous_due_at",
        "new_due_at",
        "actor",
        "reason",
        "interaction",
        "created_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: FollowUpDueDateChange | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: FollowUpDueDateChange | None = None,
    ) -> bool:
        return False


@admin.register(CareCase)
class CareCaseAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "person",
        "kind",
        "urgency",
        "status",
        "is_confidential",
        "church",
    )
    list_filter = (
        "church",
        "kind",
        "urgency",
        "status",
        "is_confidential",
    )
    search_fields = ("title", "person__full_name", "assigned_to__username")
    autocomplete_fields = (
        "person",
        "assigned_to",
        "created_by",
    )
    list_select_related = ("church", "person", "assigned_to", "created_by")
    readonly_fields = ("created_at", "updated_at")

    def get_object(
        self,
        request: HttpRequest,
        object_id: str,
        from_field: str | None = None,
    ) -> CareCase | None:
        care_case = super().get_object(request, object_id, from_field)
        if care_case is not None and care_case.is_confidential:
            record_audit_event(
                action=AuditEvent.Action.CONFIDENTIAL_CARE_VIEWED,
                actor=request.user,
                church=care_case.church,
                target=care_case,
                request=request,
            )
        return care_case


@admin.register(Interaction)
class InteractionAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "person",
        "kind",
        "visibility",
        "occurred_at",
        "author",
        "church",
    )
    list_filter = ("church", "kind", "visibility", "occurred_at")
    search_fields = ("person__full_name", "summary", "author__username")
    autocomplete_fields = (
        "person",
        "author",
        "follow_up",
        "care_case",
    )
    list_select_related = (
        "church",
        "person",
        "author",
        "follow_up",
        "care_case",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "occurred_at"
