from django.contrib import admin

from apps.companies.models import CompanyMembership
from .models import Attendance, Employee, ExpenseReport, LeaveRequest, Payslip


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


@admin.register(Employee)
class EmployeeAdmin(ScopedReadOnlyAdmin):
    list_display = ("employee_number", "user", "company", "job_title", "hire_date", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("employee_number", "user__username", "job_title")


@admin.register(LeaveRequest)
class LeaveAdmin(ScopedReadOnlyAdmin):
    list_display = ("employee", "kind", "start_date", "end_date", "status", "decided_by")
    list_filter = ("company", "status", "kind")


@admin.register(Attendance)
class AttendanceAdmin(ScopedReadOnlyAdmin):
    list_display = ("employee", "work_date", "clock_in", "clock_out", "company")
    list_filter = ("company", "work_date")


@admin.register(ExpenseReport)
class ExpenseAdmin(ScopedReadOnlyAdmin):
    list_display = ("employee", "expense_date", "category", "amount", "currency", "status", "company")
    list_filter = ("company", "status", "category")


@admin.register(Payslip)
class PayslipAdmin(ScopedReadOnlyAdmin):
    list_display = ("employee", "period_start", "period_end", "gross_amount", "deductions", "net_amount", "status", "company")
    list_filter = ("company", "status")
