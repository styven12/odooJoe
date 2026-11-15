from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "method", "path", "status_code", "ip_address")
    list_filter = ("method", "status_code", "created_at")
    search_fields = ("actor__username", "path", "ip_address")
    readonly_fields = (
        "actor", "action", "method", "path", "status_code",
        "ip_address", "user_agent", "created_at",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(actor=request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
