from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required,permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from apps.audit.models import AuditLog
from apps.companies.models import CompanyMembership
from apps.core.models import ERPModule
from apps.core.guards import require_active_company
from apps.crm.models import Partner
from .models import Asset,MaintenanceRequest,HelpdeskTicket

def enabled(request,slug):
 if not ERPModule.objects.filter(slug=slug,is_enabled=True).exists():raise Http404('Module désactivé')
 # Sans société active : les GET affichent des listes vides ; les POST sont
 # redirigés avec un message par @require_active_company.
def users(company):return get_user_model().objects.filter(company_memberships__company=company,company_memberships__is_active=True,is_active=True).distinct()
class AssetForm(forms.ModelForm):
 class Meta: model=Asset;fields=('reference','name','category','serial_number','location','purchased_on')
class MaintenanceForm(forms.ModelForm):
 class Meta: model=MaintenanceRequest;fields=('asset','title','description','priority','scheduled_for','assigned_to')
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);self.fields['asset'].queryset=Asset.objects.filter(company=company,state__in=[Asset.State.ACTIVE,Asset.State.REPAIR]);self.fields['assigned_to'].queryset=users(company)
class TicketForm(forms.ModelForm):
 class Meta: model=HelpdeskTicket;fields=('title','description','partner','priority','assigned_to')
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);self.fields['partner'].queryset=Partner.objects.filter(company=company);self.fields['assigned_to'].queryset=users(company)
@login_required
@require_active_company
@permission_required('service.view_asset',raise_exception=True)
def assets(request):
 enabled(request,'assets');form=AssetForm(request.POST or None)
 if request.method=='POST':
  if not request.user.has_perm('service.add_asset'):raise Http404
  if form.is_valid():
   asset=form.save(commit=False);asset.company=request.company
   try:asset.full_clean();asset.save()
   except ValidationError as ex:form.add_error(None,ex)
   else:messages.success(request,'Équipement enregistré.');return redirect('service:assets')
 return render(request,'service/assets.html',{'assets':Asset.objects.filter(company=request.company),'form':form})
@login_required
@require_active_company
@permission_required('service.view_maintenancerequest',raise_exception=True)
def maintenance(request):
 enabled(request,'maintenance');form=MaintenanceForm(request.POST or None,company=request.company)
 if request.method=='POST':
  if not request.user.has_perm('service.add_maintenancerequest'):raise Http404
  if form.is_valid():
   job=form.save(commit=False);job.company=request.company;job.created_by=request.user
   try:job.full_clean();job.save()
   except ValidationError as ex:form.add_error(None,ex)
   else:messages.success(request,'Intervention créée.');return redirect('service:maintenance')
 return render(request,'service/maintenance.html',{'jobs':MaintenanceRequest.objects.filter(company=request.company).select_related('asset','assigned_to'),'form':form})
@login_required
@require_POST
@require_active_company
@permission_required('service.change_maintenancerequest',raise_exception=True)
def maintenance_status(request,job_id,state):
 enabled(request,'maintenance')
 allowed={'PLANNED':{'OPEN'},'IN_PROGRESS':{'OPEN','PLANNED'},'DONE':{'IN_PROGRESS','OPEN','PLANNED'},'CANCELLED':{'OPEN','PLANNED'}}
 with transaction.atomic():
  job=get_object_or_404(MaintenanceRequest.objects.select_for_update().select_related('asset'),pk=job_id,company=request.company)
  if state not in allowed or job.state not in allowed[state]:raise Http404
  job.state=state;job.save(update_fields=['state'])
  if state=='IN_PROGRESS':job.asset.state=Asset.State.REPAIR;job.asset.save(update_fields=['state'])
  elif state=='DONE' and job.asset.state==Asset.State.REPAIR:job.asset.state=Asset.State.ACTIVE;job.asset.save(update_fields=['state'])
  AuditLog.objects.create(actor=request.user,action=f'MAINTENANCE_{state}',method='POST',path=request.path,status_code=200)
 return redirect('service:maintenance')
@login_required
@require_active_company
@permission_required('service.view_helpdeskticket',raise_exception=True)
def tickets(request):
 enabled(request,'helpdesk');form=TicketForm(request.POST or None,company=request.company)
 if request.method=='POST':
  if not request.user.has_perm('service.add_helpdeskticket'):raise Http404
  if form.is_valid():
   ticket=form.save(commit=False);ticket.company=request.company;ticket.created_by=request.user
   try:ticket.full_clean();ticket.save()
   except ValidationError as ex:form.add_error(None,ex)
   else:messages.success(request,f'Ticket {ticket.number} créé.');return redirect('service:tickets')
 ticket_rows=HelpdeskTicket.objects.filter(company=request.company)
 if not request.user.has_perm('service.change_helpdeskticket'):
  ticket_rows=ticket_rows.filter(Q(assigned_to=request.user)|Q(created_by=request.user))
 return render(request,'service/tickets.html',{'tickets':ticket_rows.select_related('partner','assigned_to'),'form':form})
@login_required
@require_POST
@require_active_company
@permission_required('service.change_helpdeskticket',raise_exception=True)
def ticket_status(request,ticket_id,state):
 enabled(request,'helpdesk');allowed={'OPEN':{'NEW','WAITING'},'WAITING':{'OPEN','NEW'},'RESOLVED':{'NEW','OPEN','WAITING'},'CLOSED':{'RESOLVED'}}
 ticket=get_object_or_404(HelpdeskTicket,pk=ticket_id,company=request.company)
 if state not in allowed or ticket.state not in allowed[state]:raise Http404
 ticket.state=state;ticket.save(update_fields=['state','updated_at']);AuditLog.objects.create(actor=request.user,action=f'TICKET_{state}',method='POST',path=request.path,status_code=200)
 return redirect('service:tickets')
