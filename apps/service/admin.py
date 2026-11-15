from django.contrib import admin

from apps.companies.models import CompanyMembership
from .models import Asset, HelpdeskTicket, MaintenanceRequest


class ScopedReadOnlyAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        company_ids = CompanyMembership.objects.filter(
            user=request.user, is_active=True
        ).values("company_id")
        return queryset.filter(company_id__in=company_ids)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Asset)
class AssetAdmin(ScopedReadOnlyAdmin):
    list_display = ("reference", "name", "company", "category", "location", "state")
    list_filter = ("company", "state", "category")
    search_fields = ("reference", "name", "serial_number")


@admin.register(MaintenanceRequest)
class MaintenanceAdmin(ScopedReadOnlyAdmin):
    list_display = ("title", "asset", "company", "priority", "state", "scheduled_for", "assigned_to")
    list_filter = ("company", "priority", "state")
    search_fields = ("title", "asset__name")


@admin.register(HelpdeskTicket)
class TicketAdmin(ScopedReadOnlyAdmin):
    list_display = ("number", "title", "company", "priority", "state", "partner", "assigned_to", "created_at")
    list_filter = ("company", "priority", "state")
    search_fields = ("number", "title", "description", "partner__name")
