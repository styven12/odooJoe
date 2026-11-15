from django.contrib import admin
from .models import ERPModule

@admin.register(ERPModule)
class ERPModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_core", "is_enabled", "version", "updated_at")
    list_filter = ("is_core", "is_enabled")
    search_fields = ("name", "slug")
    readonly_fields = ("updated_at",)
