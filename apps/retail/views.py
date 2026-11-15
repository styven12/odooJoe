from decimal import Decimal
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.audit.models import AuditLog
from apps.core.models import ERPModule
from apps.core.guards import require_active_company
from apps.crm.models import Partner
from apps.inventory.models import Product,StockMovement
from .models import RetailProduct,POSSession,POSReceipt,WebOrder

def enabled(request,slug):
 if not ERPModule.objects.filter(slug=slug,is_enabled=True).exists():raise Http404('Module désactivé')
 # Sans société active : les GET affichent des listes vides ; les POST sont
 # redirigés avec un message par @require_active_company.
class RetailProductForm(forms.ModelForm):
 class Meta:
  model=RetailProduct;fields=('product','price','online')
  labels={'product':'Article','price':'Prix de vente','online':'Visible dans la boutique'}
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);self.fields['product'].queryset=Product.objects.filter(company=company,is_active=True).exclude(retail_listing__isnull=False)
class POSSaleForm(forms.Form):
 product=forms.ModelChoiceField(queryset=Product.objects.none(),label='Article')
 quantity=forms.DecimalField(min_value=Decimal('0.001'),max_digits=12,decimal_places=3,label='Quantité')
 payment_method=forms.ChoiceField(choices=POSReceipt.Payment.choices,label='Mode de paiement')
 payment_reference=forms.CharField(required=False,max_length=100,label='Référence de paiement')
 customer_name=forms.CharField(required=False,max_length=160,label='Client')
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);self.fields['product'].queryset=Product.objects.filter(company=company,is_active=True,retail_listing__active=True).select_related('retail_listing')
 def clean(self):
  data=super().clean()
  if data.get('payment_method') in ('CARD','MOBILE') and not data.get('payment_reference'):self.add_error('payment_reference','Ajoutez la référence du paiement déjà reçu.')
  return data
class WebOrderForm(forms.Form):
 listing=forms.ModelChoiceField(queryset=RetailProduct.objects.none(),label='Article')
 customer=forms.ModelChoiceField(queryset=Partner.objects.none(),label='Client')
 quantity=forms.DecimalField(min_value=Decimal('0.001'),max_digits=12,decimal_places=3,label='Quantité')
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);self.fields['listing'].queryset=RetailProduct.objects.filter(company=company,active=True,online=True).select_related('product');self.fields['customer'].queryset=Partner.objects.filter(company=company,partner_type__in=[Partner.PartnerType.CUSTOMER,Partner.PartnerType.BOTH])
@login_required
@require_active_company
@permission_required('retail.view_possession',raise_exception=True)
def pos(request):
 enabled(request,'pos');session=POSSession.objects.filter(company=request.company,state=POSSession.State.OPEN).first();form=POSSaleForm(company=request.company)
 if request.method=='POST':
  action=request.POST.get('action')
  if action=='open':
   if not request.user.has_perm('retail.add_possession'):raise Http404
   if session:messages.error(request,'Une session de caisse est déjà ouverte.')
   else:
    try:opening=Decimal(request.POST.get('opening_cash','0'))
    except Exception:messages.error(request,'Solde initial invalide.')
    else:
     if opening<0:messages.error(request,'Le solde initial ne peut être négatif.')
     else:
      try:
       with transaction.atomic():POSSession.objects.create(company=request.company,opened_by=request.user,opening_cash=opening)
      except IntegrityError:messages.error(request,'Une session de caisse vient d’être ouverte par un autre utilisateur.')
      else:messages.success(request,'Session de caisse ouverte.')
   return redirect('retail:pos')
  if action=='close':
   if not request.user.has_perm('retail.change_possession'):raise Http404
   if not session:
    messages.error(request,'Aucune session de caisse ouverte à clôturer.');return redirect('retail:pos')
   try:counted=Decimal(request.POST.get('closing_cash',''))
   except Exception:messages.error(request,'Saisissez le montant compté en caisse.');return redirect('retail:pos')
   if counted<0:messages.error(request,'Le montant compté ne peut pas être négatif.');return redirect('retail:pos')
   with transaction.atomic():
    current=get_object_or_404(POSSession.objects.select_for_update(),pk=session.pk,company=request.company,state=POSSession.State.OPEN)
    current.closing_cash=counted;current.closed_by=request.user;current.closed_at=timezone.now();current.state=POSSession.State.CLOSED;current.save(update_fields=['closing_cash','closed_by','closed_at','state'])
   return redirect('retail:pos')
  if action=='sale':
   if not request.user.has_perm('retail.add_posreceipt'):raise Http404
   form=POSSaleForm(request.POST,company=request.company)
   if form.is_valid() and session:
    with transaction.atomic():
     current=get_object_or_404(POSSession.objects.select_for_update(),pk=session.pk,company=request.company,state=POSSession.State.OPEN)
     product=Product.objects.select_for_update().get(pk=form.cleaned_data['product'].pk,company=request.company)
     try:listing=RetailProduct.objects.get(company=request.company,product=product,active=True)
     except RetailProduct.DoesNotExist:messages.error(request,'Cet article n\'est plus en vente.');return redirect('retail:pos')
     if product.on_hand<form.cleaned_data['quantity']:messages.error(request,'Stock insuffisant.')
     else:
      StockMovement.objects.create(company=request.company,product=product,kind='OUT',quantity=form.cleaned_data['quantity'],reference='POS',created_by=request.user)
      POSReceipt.objects.create(company=request.company,session=current,product=product,quantity=form.cleaned_data['quantity'],unit_price=listing.price,payment_method=form.cleaned_data['payment_method'],payment_reference=form.cleaned_data['payment_reference'],customer_name=form.cleaned_data['customer_name'],created_by=request.user)
      AuditLog.objects.create(actor=request.user,action='POS_SALE',method='POST',path=request.path,status_code=201);messages.success(request,'Vente enregistrée et stock mis à jour.')
    return redirect('retail:pos')
   if not session:messages.error(request,'Ouvrez une session de caisse avant d’enregistrer une vente.');return redirect('retail:pos')
   if not form.is_valid():messages.error(request,'Vente non enregistrée : vérifiez les champs du formulaire.');return redirect('retail:pos')
 receipts=POSReceipt.objects.filter(company=request.company,session=session).select_related('product') if session else POSReceipt.objects.none()
 sessions=POSSession.objects.filter(company=request.company)[:20]
 return render(request,'retail/pos.html',{'session':session,'form':form,'receipts':receipts,'sessions':sessions})
@login_required
@require_active_company
@permission_required('retail.view_weborder',raise_exception=True)
def webshop(request):
 enabled(request,'ecommerce');form=WebOrderForm(company=request.company);listing_form=RetailProductForm(company=request.company)
 if request.method=='POST':
  action=request.POST.get('action')
  if action=='listing':
   if not request.user.has_perm('retail.add_retailproduct'):raise Http404
   listing_form=RetailProductForm(request.POST,company=request.company)
   if listing_form.is_valid():
    listing=listing_form.save(commit=False);listing.company=request.company
    try:listing.full_clean();listing.save()
    except ValidationError as ex:listing_form.add_error(None,ex)
    else:messages.success(request,'Article ajouté au catalogue.');return redirect('retail:webshop')
  elif action=='order':
   if not request.user.has_perm('retail.add_weborder'):raise Http404
   form=WebOrderForm(request.POST,company=request.company)
   if form.is_valid():
    listing=form.cleaned_data['listing'];order=WebOrder(company=request.company,customer=form.cleaned_data['customer'],product=listing.product,quantity=form.cleaned_data['quantity'],unit_price=listing.price)
    try:order.full_clean();order.save()
    except ValidationError as ex:form.add_error(None,ex)
    else:messages.success(request,f'Commande web {order.number} créée en attente de confirmation.');return redirect('retail:webshop')
 orders=WebOrder.objects.filter(company=request.company).select_related('customer','product')[:100]
 listings=RetailProduct.objects.filter(company=request.company,active=True,online=True).select_related('product')
 return render(request,'retail/webshop.html',{'form':form,'listing_form':listing_form,'orders':orders,'listings':listings})
@login_required
@require_POST
@require_active_company
@permission_required('retail.change_weborder',raise_exception=True)
def confirm_web_order(request,order_id):
 enabled(request,'ecommerce')
 with transaction.atomic():
  order=get_object_or_404(WebOrder.objects.select_for_update(),pk=order_id,company=request.company,state=WebOrder.State.PENDING)
  product=Product.objects.select_for_update().get(pk=order.product_id,company=request.company)
  if product.on_hand<order.quantity:messages.error(request,'Stock insuffisant pour confirmer cette commande.')
  else:
   StockMovement.objects.create(company=request.company,product=product,kind='OUT',quantity=order.quantity,reference=order.number,created_by=request.user)
   order.state=WebOrder.State.CONFIRMED;order.confirmed_by=request.user;order.save(update_fields=['state','confirmed_by']);messages.success(request,'Commande confirmée et stock mis à jour.')
 return redirect('retail:webshop')
