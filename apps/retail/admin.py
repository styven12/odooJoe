from django.contrib import admin

from apps.companies.models import CompanyMembership
from .models import POSReceipt, POSSession, RetailProduct, WebOrder


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


@admin.register(RetailProduct)
class RetailProductAdmin(ScopedReadOnlyAdmin):
    list_display = ("product", "company", "price", "online", "active")
    list_filter = ("company", "active", "online")


@admin.register(POSSession)
class POSSessionAdmin(ScopedReadOnlyAdmin):
    list_display = ("company", "opened_by", "opened_at", "state", "opening_cash", "closing_cash")
    list_filter = ("company", "state")


@admin.register(POSReceipt)
class POSReceiptAdmin(ScopedReadOnlyAdmin):
    list_display = ("number", "company", "session", "product", "quantity", "unit_price", "payment_method", "created_at")
    list_filter = ("company", "payment_method")


@admin.register(WebOrder)
class WebOrderAdmin(ScopedReadOnlyAdmin):
    list_display = ("number", "company", "customer", "product", "quantity", "state", "created_at")
    list_filter = ("company", "state")
