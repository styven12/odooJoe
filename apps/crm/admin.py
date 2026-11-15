from django.contrib import admin

from apps.companies.models import CompanyMembership
from .models import Activity, Lead, Opportunity, Partner


class CompanyScopedAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(
            company__memberships__user=request.user,
            company__memberships__is_active=True,
        ).distinct()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            allowed = CompanyMembership.objects.filter(user=request.user, is_active=True).values("company_id")
            if db_field.name == "company":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(pk__in=allowed, is_active=True)
            elif db_field.name == "partner":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(company_id__in=allowed)
            elif db_field.name in ("lead", "opportunity"):
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(company_id__in=allowed)
            elif db_field.name == "assigned_to":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    company_memberships__company_id__in=allowed,
                    company_memberships__is_active=True,
                    is_active=True,
                ).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Partner)
class PartnerAdmin(CompanyScopedAdmin):
    list_display = ("name", "partner_type", "company", "email", "phone", "city")
    list_filter = ("company", "partner_type", "city")
    search_fields = ("name", "email", "phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Lead)
class LeadAdmin(CompanyScopedAdmin):
    list_display = ("title", "partner", "company", "status", "assigned_to", "created_at")
    list_filter = ("company", "status", "source")
    search_fields = ("title", "contact_name", "email", "phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Opportunity)
class OpportunityAdmin(CompanyScopedAdmin):
    list_display = ("name", "partner", "company", "stage", "expected_revenue", "probability", "assigned_to")
    list_filter = ("company", "stage", "assigned_to")
    search_fields = ("name", "partner__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Activity)
class ActivityAdmin(CompanyScopedAdmin):
    list_display = ("title", "company", "activity_type", "status", "due_at", "assigned_to")
    list_filter = ("company", "activity_type", "status", "assigned_to")
    search_fields = ("title", "notes")
    readonly_fields = ("created_at",)
