from django.contrib import admin
from django.http import HttpRequest

from config.admin import SuperuserOnlyAdminMixin

from .models import Household, Person, Relationship


@admin.register(Household)
class HouseholdAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "church", "updated_at")
    list_filter = ("church",)
    search_fields = ("name", "church__name")
    list_select_related = ("church",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Person)
class PersonAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
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
    readonly_fields = ("created_at", "updated_at")

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
