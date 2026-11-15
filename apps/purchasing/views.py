from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.audit.models import AuditLog
from apps.core.models import ERPModule
from apps.core.guards import require_active_company
from apps.crm.models import Partner
from apps.inventory.models import Product, StockMovement
from .models import PurchaseOrder

def enabled(request):
    if not ERPModule.objects.filter(slug='purchasing',is_enabled=True).exists(): raise Http404('Module désactivé')
    # Sans société active : les GET affichent des listes vides ; les POST sont
    # redirigés avec un message par @require_active_company.
class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model=PurchaseOrder
        fields=('supplier','product','quantity','unit_cost','notes')
        labels={'supplier':'Fournisseur','product':'Article','quantity':'Quantité','unit_cost':'Coût unitaire','notes':'Notes'}
    def __init__(self,*args,company,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['supplier'].queryset=Partner.objects.filter(company=company,partner_type__in=[Partner.PartnerType.SUPPLIER,Partner.PartnerType.BOTH])
        self.fields['product'].queryset=Product.objects.filter(company=company,is_active=True)
@login_required
@permission_required('purchasing.view_purchaseorder',raise_exception=True)
def order_list(request):
    enabled(request)
    return render(request,'purchasing/order_list.html',{'orders':PurchaseOrder.objects.filter(company=request.company).select_related('supplier','product')})
@login_required
@require_active_company
@permission_required('purchasing.add_purchaseorder',raise_exception=True)
def create_order(request):
    enabled(request)
    if request.method=='POST':
        form=PurchaseOrderForm(request.POST,company=request.company)
        if form.is_valid():
            order=form.save(commit=False); order.company=request.company; order.currency=request.company.currency; order.created_by=request.user
            try: order.full_clean(); order.save()
            except ValidationError as error: form.add_error(None,error)
            else: messages.success(request,f'Commande fournisseur {order.number} créée.'); return redirect('purchasing:orders')
    else: form=PurchaseOrderForm(company=request.company)
    return render(request,'purchasing/order_form.html',{'form':form})
@login_required
@require_POST
@require_active_company
@permission_required('purchasing.change_purchaseorder',raise_exception=True)
def order_action(request,order_id,action):
    enabled(request)
    with transaction.atomic():
        order=get_object_or_404(PurchaseOrder.objects.select_for_update(),pk=order_id,company=request.company)
        if action=='order' and order.status==PurchaseOrder.Status.DRAFT: order.status=PurchaseOrder.Status.ORDERED
        elif action=='receive' and order.status==PurchaseOrder.Status.ORDERED:
            order.status=PurchaseOrder.Status.RECEIVED
            StockMovement.objects.create(company=order.company,product=order.product,kind='IN',quantity=order.quantity,reference=order.number,created_by=request.user)
        elif action=='cancel' and order.status in [PurchaseOrder.Status.DRAFT,PurchaseOrder.Status.ORDERED]: order.status=PurchaseOrder.Status.CANCELLED
        else: messages.info(request,'Cette transition n’est pas autorisée.'); return redirect('purchasing:orders')
        order.save(update_fields=['status','updated_at'])
        AuditLog.objects.create(actor=request.user,action=f'PURCHASE_{action.upper()}',method='POST',path=request.path,status_code=200)
        messages.success(request,'Statut de la commande mis à jour.')
    return redirect('purchasing:orders')
