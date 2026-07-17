from django.contrib import admin
from django.http import HttpRequest

from config.admin import SuperuserOnlyAdminMixin

from .lifecycle import deactivate_person
from .models import ConsentRecord, Household, Person, Relationship


@admin.register(Household)
class HouseholdAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "church", "updated_at")
    list_filter = ("church",)
    search_fields = ("name", "church__name")
    list_select_related = ("church",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Person)
class PersonAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    actions = ("deactivate_selected_people",)
    sensitive_fields = ("discipleship_stage", "faith_background")
    list_display = (
        "full_name",
        "preferred_name",
        "church",
        "membership_status",
        "email",
        "phone",
        "updated_at",
    )
    list_filter = (
        "church",
        "membership_status",
        "gender",
        "has_whatsapp",
    )
    search_fields = ("full_name", "preferred_name", "email", "phone")
    autocomplete_fields = ("household", "invited_by")
    list_select_related = ("church", "household", "invited_by")
    readonly_fields = (
        "created_at",
        "updated_at",
        "deactivated_at",
        "anonymized_at",
    )

    @admin.action(description="Deactivate selected people (preserves history)")
    def deactivate_selected_people(
        self,
        request: HttpRequest,
        queryset,
    ) -> None:
        count = 0
        for person in queryset:
            was_active = person.membership_status != Person.MembershipStatus.INACTIVE
            deactivate_person(person)
            count += int(was_active)
        self.message_user(request, f"Deactivated {count} people.")

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: object | None = None,
    ) -> bool:
        return False

    def get_exclude(
        self,
        request: HttpRequest,
        obj: Person | None = None,
    ) -> tuple[str, ...] | None:
        excluded = tuple(super().get_exclude(request, obj) or ())
        if request.user.is_superuser:
            return excluded or None
        return (*excluded, *self.sensitive_fields)


@admin.register(Relationship)
class RelationshipAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("from_person", "to_person", "kind", "church", "updated_at")
    list_filter = ("church", "kind")
    search_fields = ("from_person__full_name", "to_person__full_name")
    autocomplete_fields = ("from_person", "to_person")
    list_select_related = ("church", "from_person", "to_person")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ConsentRecord)
class ConsentRecordAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "person",
        "status",
        "notice_version",
        "consented_at",
        "method",
        "recorded_by",
        "church",
    )
    list_filter = ("church", "status", "method", "notice_version", "consented_at")
    search_fields = (
        "person__full_name",
        "recorded_by__username",
        "notice_version",
    )
    list_select_related = ("church", "person", "recorded_by", "supersedes")
    date_hierarchy = "consented_at"
    readonly_fields = (
        "church",
        "person",
        "status",
        "notice_version",
        "consented_at",
        "method",
        "recorded_by",
        "supersedes",
        "created_at",
        "updated_at",
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
