from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from config.admin import SuperuserOnlyAdminMixin

from .models import ChurchMembership, User


@admin.register(User)
class UserAdmin(SuperuserOnlyAdminMixin, DjangoUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email")


@admin.register(ChurchMembership)
class ChurchMembershipAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("user", "church", "person", "role", "is_active", "updated_at")
    list_filter = ("church", "role", "is_active")
    search_fields = (
        "user__username",
        "user__email",
        "person__full_name",
        "church__name",
    )
    autocomplete_fields = ("user", "church", "person")
    list_select_related = ("user", "church", "person")
    readonly_fields = ("created_at", "updated_at")
