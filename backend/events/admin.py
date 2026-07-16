from django.contrib import admin

from config.admin import SuperuserOnlyAdminMixin

from .models import Event, EventRegistration


@admin.register(Event)
class EventAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "church",
        "group",
        "starts_at",
        "capacity",
        "signup_opens",
    )
    list_filter = ("church", "signup_opens", "starts_at")
    search_fields = ("title", "description", "location", "group__name")
    autocomplete_fields = ("group", "created_by")
    list_select_related = ("church", "group", "created_by")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "starts_at"


@admin.register(EventRegistration)
class EventRegistrationAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "person",
        "event",
        "status",
        "needs_transport",
        "checked_in_at",
        "church",
    )
    list_filter = ("church", "status", "needs_transport", "checkin_method")
    search_fields = ("person__full_name", "event__title", "note")
    autocomplete_fields = ("event", "person")
    list_select_related = ("church", "event", "person")
    readonly_fields = ("created_at", "updated_at", "registered_at")
    date_hierarchy = "registered_at"
