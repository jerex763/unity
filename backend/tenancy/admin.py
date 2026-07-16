from django.contrib import admin

from config.admin import SuperuserOnlyAdminMixin

from .models import Church


@admin.register(Church)
class ChurchAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("name", "timezone", "locale", "updated_at")
    search_fields = ("name", "timezone", "locale")
    readonly_fields = ("created_at", "updated_at")
