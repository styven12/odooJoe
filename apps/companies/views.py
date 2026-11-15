from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Company


@login_required
@require_POST
def select_company(request):
    company = Company.objects.filter(pk=request.POST.get("company_id"), is_active=True)
    if not request.user.is_superuser:
        company = company.filter(memberships__user=request.user, memberships__is_active=True)
    selected = company.first()
    if selected:
        request.session["active_company_id"] = selected.pk
        messages.success(request, f"Société active : {selected.name}")
    else:
        messages.error(request, "Vous n’avez pas accès à cette société.")
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("dashboard")
