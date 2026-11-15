from django.contrib import admin

from apps.companies.models import CompanyMembership
from .models import JournalEntry, LedgerAccount, TreasuryAccount, TreasuryMovement


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


@admin.register(LedgerAccount)
class LedgerAccountAdmin(ScopedReadOnlyAdmin):
    list_display = ("code", "name", "kind", "company", "is_active")
    list_filter = ("company", "kind", "is_active")
    search_fields = ("code", "name")


@admin.register(JournalEntry)
class JournalEntryAdmin(ScopedReadOnlyAdmin):
    list_display = ("number", "entry_date", "description", "amount", "state", "company")
    list_filter = ("company", "state", "entry_date")
    search_fields = ("number", "description")


@admin.register(TreasuryAccount)
class TreasuryAccountAdmin(ScopedReadOnlyAdmin):
    list_display = ("name", "kind", "currency", "opening_balance", "company", "is_active")
    list_filter = ("company", "kind", "is_active")


@admin.register(TreasuryMovement)
class TreasuryMovementAdmin(ScopedReadOnlyAdmin):
    list_display = ("movement_date", "account", "direction", "amount", "description", "company")
    list_filter = ("company", "direction", "movement_date")
