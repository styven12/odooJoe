from django.contrib import admin
from .models import Company, CompanyMembership

class CompanyMembershipInline(admin.TabularInline):
    model = CompanyMembership
    extra = 0

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(company__memberships__user=request.user, company__memberships__is_active=True).distinct()

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "city", "country", "currency", "is_active")
    search_fields = ("name", "code", "tax_id")
    list_filter = ("is_active", "country")
    inlines = [CompanyMembershipInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(memberships__user=request.user, memberships__is_active=True).distinct()

@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ("company", "user", "role", "is_active")
    list_filter = ("role", "is_active", "company")
    search_fields = ("company__name", "user__username", "user__email")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(company__memberships__user=request.user, company__memberships__is_active=True).distinct()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            company_ids = CompanyMembership.objects.filter(user=request.user, is_active=True).values("company_id")
            if db_field.name == "company":
                kwargs["queryset"] = Company.objects.filter(pk__in=company_ids, is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
