from django.contrib import admin

from config.admin import SuperuserOnlyAdminMixin

from .models import Group, GroupMembership


@admin.register(Group)
class GroupAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "church", "kind", "health", "is_active", "updated_at")
    list_filter = ("church", "kind", "health", "is_active")
    search_fields = ("name", "description", "location")
    list_select_related = ("church",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(GroupMembership)
class GroupMembershipAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("person", "group", "role", "church", "joined_at", "left_at")
    list_filter = ("church", "role", "joined_at", "left_at")
    search_fields = ("person__full_name", "group__name")
    autocomplete_fields = ("group", "person")
    list_select_related = ("church", "group", "person")
    readonly_fields = ("created_at", "updated_at")
