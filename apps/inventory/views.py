from decimal import Decimal
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Case, When, F, DecimalField, Value
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.audit.models import AuditLog
from apps.core.models import ERPModule
from apps.core.guards import require_active_company
from .models import Product, StockMovement

def enabled(request):
    if not ERPModule.objects.filter(slug='inventory', is_enabled=True).exists(): raise Http404('Module désactivé')
    # Sans société active : les GET affichent des listes vides ; les POST sont
    # redirigés avec un message par @require_active_company.

class ProductForm(forms.ModelForm):
    class Meta:
        model=Product
        fields=('sku','name','unit','reorder_level')
class MovementForm(forms.ModelForm):
    class Meta:
        model=StockMovement
        fields=('product','kind','quantity','reference')
    def __init__(self,*args,company,**kwargs):
        super().__init__(*args,**kwargs); self.fields['product'].queryset=Product.objects.filter(company=company,is_active=True)

@login_required
@permission_required('inventory.view_product',raise_exception=True)
def stock_list(request):
    enabled(request)
    products=Product.objects.filter(company=request.company,is_active=True)
    rows=[{'product':p,'on_hand':p.on_hand} for p in products]
    return render(request,'inventory/stock_list.html',{'rows':rows,'movements':StockMovement.objects.filter(company=request.company).select_related('product','created_by')[:20]})

@login_required
@require_POST
@require_active_company
@permission_required('inventory.add_product',raise_exception=True)
def create_product(request):
    enabled(request); form=ProductForm(request.POST)
    if form.is_valid():
        product=form.save(commit=False); product.company=request.company; product.save(); messages.success(request,'Article créé.')
    else: messages.error(request,form.errors.as_text())
    return redirect('inventory:stock')

@login_required
@require_POST
@require_active_company
@permission_required('inventory.add_stockmovement',raise_exception=True)
def move_stock(request):
    enabled(request); form=MovementForm(request.POST,company=request.company)
    if form.is_valid():
        movement=form.save(commit=False); movement.company=request.company; movement.created_by=request.user
        with transaction.atomic():
            product=Product.objects.select_for_update().get(pk=movement.product_id,company=request.company)
            current=product.on_hand
            if movement.kind=='OUT' and movement.quantity>current:
                messages.error(request,'Stock insuffisant pour cette sortie.')
            else:
                movement.save(); AuditLog.objects.create(actor=request.user,action=f'STOCK_{movement.kind}',method='POST',path=request.path,status_code=200); messages.success(request,'Mouvement de stock enregistré.')
    else: messages.error(request,form.errors.as_text())
    return redirect('inventory:stock')
