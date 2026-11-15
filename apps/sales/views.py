from functools import wraps
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.audit.models import AuditLog
from apps.core.models import ERPModule
from apps.crm.models import Opportunity
from .models import Invoice, SalesOrder


def module_enabled(slug):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not ERPModule.objects.filter(slug=slug, is_enabled=True).exists():
                from django.http import Http404
                raise Http404("Ce module est désactivé.")
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def csv_download(filename, headers, rows):
    from django.http import HttpResponse
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow([_csv_value(value) for value in headers])
    writer.writerows([_csv_value(value) for value in row] for row in rows)
    return response


def _csv_value(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


@login_required
@module_enabled("sales")
@permission_required("sales.view_salesorder", raise_exception=True)
def order_list(request):
    orders = SalesOrder.objects.filter(company=request.company).select_related("customer", "opportunity") if request.company else SalesOrder.objects.none()
    return render(request, "sales/order_list.html", {"orders": orders})


@login_required
@module_enabled("sales")
@permission_required("sales.view_salesorder", raise_exception=True)
def export_orders(request):
    orders = SalesOrder.objects.filter(company=request.company).select_related("customer", "opportunity") if request.company else SalesOrder.objects.none()
    return csv_download("commandes.csv", ("Référence", "Client", "Opportunité", "Montant", "Devise", "État", "Créée le"), (
        (order.number, order.customer.name, order.opportunity.name, order.amount, order.currency, order.get_state_display(), order.created_at.isoformat())
        for order in orders
    ))


@login_required
@module_enabled("invoicing")
@permission_required("sales.view_invoice", raise_exception=True)
def invoice_list(request):
    invoices = Invoice.objects.filter(company=request.company).select_related("customer", "sales_order") if request.company else Invoice.objects.none()
    return render(request, "sales/invoice_list.html", {"invoices": invoices})


@login_required
@module_enabled("invoicing")
@permission_required("sales.view_invoice", raise_exception=True)
def export_invoices(request):
    invoices = Invoice.objects.filter(company=request.company).select_related("customer", "sales_order") if request.company else Invoice.objects.none()
    return csv_download("factures.csv", ("Référence", "Client", "Commande", "Montant", "Devise", "État", "Émise le", "Échéance"), (
        (invoice.number, invoice.customer.name, invoice.sales_order.number, invoice.amount, invoice.currency, invoice.get_status_display(), invoice.issued_at.isoformat(), invoice.due_date or "")
        for invoice in invoices
    ))


@login_required
@require_POST
@module_enabled("sales")
@permission_required("sales.add_salesorder", raise_exception=True)
def create_quote(request, opportunity_id):
    if not request.company:
        messages.error(request, "Aucune société active n’est associée à votre compte.")
        return redirect("crm:index")
    opportunity = get_object_or_404(
        Opportunity.objects.select_related("partner"),
        pk=opportunity_id,
        company=request.company,
    )
    quote = SalesOrder.objects.create(
        company=request.company,
        customer=opportunity.partner,
        opportunity=opportunity,
        amount=opportunity.expected_revenue,
        currency=request.company.currency,
        created_by=request.user,
    )
    AuditLog.objects.create(actor=request.user, action="QUOTE_CREATED", method="POST", path=request.path, status_code=201)
    messages.success(request, f"Le devis {quote.number} a été créé.")
    return redirect("sales:orders")


@login_required
@require_POST
@module_enabled("sales")
@permission_required("sales.confirm_salesorder", raise_exception=True)
def confirm_order(request, order_id):
    if not request.company:
        return HttpResponseForbidden("Aucune société active.")
    with transaction.atomic():
        order = get_object_or_404(
            SalesOrder.objects.select_for_update(),
            pk=order_id,
            company=request.company,
        )
        if order.state == SalesOrder.State.CANCELLED:
            messages.error(request, "Un devis annulé ne peut pas être confirmé.")
            return redirect("sales:orders")
        if order.state == SalesOrder.State.QUOTATION:
            order.state = SalesOrder.State.CONFIRMED
            order.save(update_fields=["state", "updated_at"])
            invoice = Invoice.objects.create(
                company=order.company,
                sales_order=order,
                customer=order.customer,
                amount=order.amount,
                currency=order.currency,
                created_by=request.user,
            )
            AuditLog.objects.create(actor=request.user, action="ORDER_CONFIRMED", method="POST", path=request.path, status_code=200)
            messages.success(request, f"Commande confirmée ; facture {invoice.number} créée.")
        else:
            messages.info(request, "Cette commande est déjà confirmée.")
    return redirect("sales:invoices")


@login_required
@require_POST
@module_enabled("invoicing")
@permission_required("sales.change_invoice", raise_exception=True)
def mark_invoice_paid(request, invoice_id):
    if not request.company:
        return HttpResponseForbidden("Aucune société active.")
    with transaction.atomic():
        invoice = get_object_or_404(
            Invoice.objects.select_for_update(),
            pk=invoice_id,
            company=request.company,
        )
        if invoice.status == Invoice.Status.OPEN:
            invoice.status = Invoice.Status.PAID
            invoice.paid_at = timezone.now()
            invoice.save(update_fields=["status", "paid_at"])
            AuditLog.objects.create(actor=request.user, action="INVOICE_PAID", method="POST", path=request.path, status_code=200)
            messages.success(request, f"La facture {invoice.number} est marquée comme payée.")
        else:
            messages.info(request, "Cette facture n’est plus en attente de paiement.")
    return redirect("sales:invoices")
