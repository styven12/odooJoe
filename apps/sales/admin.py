from django.contrib import admin

from apps.companies.models import CompanyMembership
from .models import Invoice, SalesOrder


class CompanyScopedSalesAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset.filter(company__is_active=True)
        company_ids = CompanyMembership.objects.filter(user=request.user, is_active=True, company__is_active=True).values("company_id")
        return queryset.filter(company_id__in=company_ids)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            company_ids = CompanyMembership.objects.filter(user=request.user, is_active=True, company__is_active=True).values("company_id")
            if db_field.name == "company":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(pk__in=company_ids)
            elif db_field.name in ("customer", "opportunity", "sales_order"):
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(company_id__in=company_ids)
            elif db_field.name == "created_by":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    company_memberships__company_id__in=company_ids,
                    company_memberships__is_active=True,
                ).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SalesOrder)
class SalesOrderAdmin(CompanyScopedSalesAdmin):
    list_display = ("number", "customer", "company", "amount", "currency", "state", "created_at")
    list_filter = ("state", "company", "currency")
    search_fields = ("number", "customer__name", "opportunity__name")
    readonly_fields = ("number", "created_at", "updated_at")


@admin.register(Invoice)
class InvoiceAdmin(CompanyScopedSalesAdmin):
    list_display = ("number", "customer", "company", "amount", "currency", "status", "issued_at", "due_date")
    list_filter = ("status", "company", "currency")
    search_fields = ("number", "customer__name", "sales_order__number")
    readonly_fields = ("number", "issued_at", "paid_at")
