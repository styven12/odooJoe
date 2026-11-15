from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.audit.models import AuditLog
from .models import ERPModule

IMPLEMENTED_MODULES = {"crm", "sales", "invoicing", "inventory", "purchasing", "projects", "timesheets", "employees", "leaves", "attendance", "expenses", "assets", "maintenance", "helpdesk", "manufacturing", "shipping", "documents", "payroll", "accounting", "treasury", "pos", "ecommerce"}

@login_required
def dashboard(request):
    memberships = request.user.company_memberships.filter(is_active=True)
    if request.company:
        memberships = memberships.filter(company=request.company)
    enabled_slugs = set(ERPModule.objects.filter(is_enabled=True).values_list("slug", flat=True))
    context = {
        "users_count": memberships.values("user_id").distinct().count() if request.company else 0,
        "companies_count": len(request.available_companies),
        "modules_count": ERPModule.objects.count(),
        "enabled_modules_count": ERPModule.objects.filter(is_enabled=True).count(),
        "recent_audits": AuditLog.objects.filter(actor=request.user).select_related("actor")[:8],
        "modules": ERPModule.objects.all()[:8],
        "active_company": request.company,
        "sales_enabled": "sales" in enabled_slugs,
        "invoicing_enabled": "invoicing" in enabled_slugs,
        "inventory_enabled": "inventory" in enabled_slugs,
        "purchasing_enabled": "purchasing" in enabled_slugs,
        "projects_enabled": "projects" in enabled_slugs,
        "timesheets_enabled": "timesheets" in enabled_slugs,
        "employees_enabled": "employees" in enabled_slugs,
        "leaves_enabled": "leaves" in enabled_slugs,
        "attendance_enabled": "attendance" in enabled_slugs,
        "expenses_enabled": "expenses" in enabled_slugs,
        "assets_enabled": "assets" in enabled_slugs,
        "maintenance_enabled": "maintenance" in enabled_slugs,
        "helpdesk_enabled": "helpdesk" in enabled_slugs,
        "manufacturing_enabled": "manufacturing" in enabled_slugs,
        "shipping_enabled": "shipping" in enabled_slugs,
        "documents_enabled": "documents" in enabled_slugs,
        "payroll_enabled": "payroll" in enabled_slugs,
        "accounting_enabled": "accounting" in enabled_slugs,
        "treasury_enabled": "treasury" in enabled_slugs,
        "pos_enabled": "pos" in enabled_slugs,
        "ecommerce_enabled": "ecommerce" in enabled_slugs,
    }
    return render(request, "core/dashboard.html", context)

@login_required
@permission_required("core.view_erpmodule", raise_exception=True)
def module_list(request):
    modules = list(ERPModule.objects.all())
    for module in modules:
        module.is_implemented = module.slug in IMPLEMENTED_MODULES
    return render(request, "core/module_list.html", {"modules": modules})

@login_required
@require_POST
@permission_required("core.change_erpmodule", raise_exception=True)
def toggle_module(request, slug):
    module = get_object_or_404(ERPModule, slug=slug, is_core=False)
    if module.slug not in IMPLEMENTED_MODULES:
        messages.warning(request, "Ce module est encore une fiche catalogue et ne peut pas être activé.")
        return redirect("module_list")
    module.is_enabled = not module.is_enabled
    module.save(update_fields=["is_enabled", "updated_at"])
    state = "activé" if module.is_enabled else "désactivé"
    messages.success(request, f"Le module {module.name} a été {state}.")
    return redirect("module_list")
