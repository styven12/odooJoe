from decimal import Decimal
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from apps.audit.models import AuditLog
from apps.core.models import ERPModule
from apps.core.guards import require_active_company
from apps.inventory.models import Product,StockMovement
from apps.sales.models import SalesOrder
from .models import BillOfMaterials,ManufacturingOrder,Shipment

def enabled(request,slug):
 if not ERPModule.objects.filter(slug=slug,is_enabled=True).exists():raise Http404('Module désactivé')
 # Sans société active : les GET affichent des listes vides ; les POST sont
 # redirigés avec un message par @require_active_company.
class BOMForm(forms.ModelForm):
 class Meta: model=BillOfMaterials;fields=('product','component','quantity')
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);q=Product.objects.filter(company=company,is_active=True);self.fields['product'].queryset=q;self.fields['component'].queryset=q
class ManufacturingForm(forms.ModelForm):
 class Meta: model=ManufacturingOrder;fields=('product','quantity')
 def __init__(self,*args,company,**kwargs):super().__init__(*args,**kwargs);self.fields['product'].queryset=Product.objects.filter(company=company,is_active=True)
class ShipmentForm(forms.ModelForm):
 class Meta: model=Shipment;fields=('order','product','quantity','carrier','tracking_reference')
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);self.fields['order'].queryset=SalesOrder.objects.filter(company=company,state=SalesOrder.State.CONFIRMED);self.fields['product'].queryset=Product.objects.filter(company=company,is_active=True)
@login_required
@require_active_company
@permission_required('production.view_manufacturingorder',raise_exception=True)
def manufacturing(request):
 enabled(request,'manufacturing')
 return render(request,'production/manufacturing.html',{'boms':BillOfMaterials.objects.filter(company=request.company).select_related('product','component'),'orders':ManufacturingOrder.objects.filter(company=request.company).select_related('product'),'bom_form':BOMForm(company=request.company),'order_form':ManufacturingForm(company=request.company)})
@login_required
@require_POST
@require_active_company
@permission_required('production.add_billofmaterials',raise_exception=True)
def create_bom(request):
 enabled(request,'manufacturing');form=BOMForm(request.POST,company=request.company)
 if form.is_valid():
  bom=form.save(commit=False);bom.company=request.company
  try:bom.full_clean();bom.save()
  except ValidationError as e:form.add_error(None,e)
  else:messages.success(request,'Composant ajouté à la nomenclature.');return redirect('production:manufacturing')
 messages.error(request,form.errors.as_text());return redirect('production:manufacturing')
@login_required
@require_POST
@require_active_company
@permission_required('production.add_manufacturingorder',raise_exception=True)
def create_mo(request):
 enabled(request,'manufacturing');form=ManufacturingForm(request.POST,company=request.company)
 if form.is_valid():
  order=form.save(commit=False);order.company=request.company;order.created_by=request.user
  try:order.full_clean();order.save()
  except ValidationError as e:messages.error(request,str(e))
  else:messages.success(request,f'Ordre {order.number} créé.');return redirect('production:manufacturing')
 messages.error(request,form.errors.as_text());return redirect('production:manufacturing')
@login_required
@require_POST
@require_active_company
@permission_required('production.change_manufacturingorder',raise_exception=True)
def mo_action(request,order_id,action):
 enabled(request,'manufacturing')
 with transaction.atomic():
  order=get_object_or_404(ManufacturingOrder.objects.select_for_update(),pk=order_id,company=request.company)
  recipe=list(BillOfMaterials.objects.filter(company=request.company,product=order.product).select_related('component'))
  if action=='start' and order.state==ManufacturingOrder.State.DRAFT and recipe:
   order.state=ManufacturingOrder.State.IN_PROGRESS
  elif action=='complete' and order.state==ManufacturingOrder.State.IN_PROGRESS and recipe:
   product_ids=sorted({line.component_id for line in recipe}|{order.product_id})
   list(Product.objects.select_for_update().filter(pk__in=product_ids).order_by('pk'))
   insufficient=[f'{line.component.name}: {line.component.on_hand} disponible(s), {line.quantity*order.quantity} requis' for line in recipe if line.component.on_hand < line.quantity*order.quantity]
   if insufficient:messages.error(request,'Stock insuffisant : '+'; '.join(insufficient));return redirect('production:manufacturing')
   for line in recipe:StockMovement.objects.create(company=request.company,product=line.component,kind='OUT',quantity=line.quantity*order.quantity,reference=order.number,created_by=request.user)
   StockMovement.objects.create(company=request.company,product=order.product,kind='IN',quantity=order.quantity,reference=order.number,created_by=request.user)
   order.state=ManufacturingOrder.State.DONE
  elif action=='cancel' and order.state in (ManufacturingOrder.State.DRAFT,ManufacturingOrder.State.IN_PROGRESS):order.state=ManufacturingOrder.State.CANCELLED
  else:raise Http404
  order.save(update_fields=['state']);AuditLog.objects.create(actor=request.user,action=f'MANUFACTURING_{action.upper()}',method='POST',path=request.path,status_code=200)
 return redirect('production:manufacturing')
@login_required
@require_active_company
@permission_required('production.view_shipment',raise_exception=True)
def shipments(request):
 enabled(request,'shipping');form=ShipmentForm(company=request.company)
 if request.method=='POST':
  if not request.user.has_perm('production.add_shipment'):raise Http404
  form=ShipmentForm(request.POST,company=request.company)
  if form.is_valid():
   shipment=form.save(commit=False);shipment.company=request.company;shipment.created_by=request.user
   try:shipment.full_clean();shipment.save()
   except ValidationError as ex:form.add_error(None,ex)
   else:messages.success(request,f'Expédition {shipment.number} préparée.');return redirect('production:shipments')
 return render(request,'production/shipments.html',{'shipments':Shipment.objects.filter(company=request.company).select_related('order','product'),'form':form})
@login_required
@require_POST
@require_active_company
@permission_required('production.change_shipment',raise_exception=True)
def shipment_action(request,shipment_id,state):
 enabled(request,'shipping')
 with transaction.atomic():
  shipment=get_object_or_404(Shipment.objects.select_for_update(),pk=shipment_id,company=request.company)
  if state=='SHIPPED' and shipment.state==Shipment.State.READY:
   product=Product.objects.select_for_update().get(pk=shipment.product_id,company=request.company)
   if product.on_hand<shipment.quantity:messages.error(request,'Stock insuffisant pour expédier cette quantité.');return redirect('production:shipments')
   StockMovement.objects.create(company=request.company,product=product,kind='OUT',quantity=shipment.quantity,reference=shipment.number,created_by=request.user);shipment.state=Shipment.State.SHIPPED
  elif state=='DELIVERED' and shipment.state==Shipment.State.SHIPPED:shipment.state=Shipment.State.DELIVERED
  elif state=='CANCELLED' and shipment.state==Shipment.State.READY:shipment.state=Shipment.State.CANCELLED
  else:raise Http404
  shipment.save(update_fields=['state']);AuditLog.objects.create(actor=request.user,action=f'SHIPMENT_{state}',method='POST',path=request.path,status_code=200)
 return redirect('production:shipments')
