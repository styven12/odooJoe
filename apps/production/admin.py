from django.contrib import admin

from apps.companies.models import CompanyMembership
from .models import BillOfMaterials, ManufacturingOrder, Shipment


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


@admin.register(BillOfMaterials)
class BOMAdmin(ScopedReadOnlyAdmin):
    list_display = ("product", "component", "quantity", "company")
    list_filter = ("company",)
    search_fields = ("product__name", "component__name")


@admin.register(ManufacturingOrder)
class MOAdmin(ScopedReadOnlyAdmin):
    list_display = ("number", "product", "quantity", "state", "company", "created_at")
    list_filter = ("company", "state")
    search_fields = ("number", "product__name")


@admin.register(Shipment)
class ShipmentAdmin(ScopedReadOnlyAdmin):
    list_display = ("number", "order", "product", "quantity", "state", "company")
    list_filter = ("company", "state")
    search_fields = ("number", "order__number", "product__name")
