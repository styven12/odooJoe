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
from .models import LedgerAccount,JournalEntry,TreasuryAccount,TreasuryMovement

def enabled(request,slug):
 if not ERPModule.objects.filter(slug=slug,is_enabled=True).exists():raise Http404('Module désactivé')
 # Sans société active : les GET affichent des listes vides ; les POST sont
 # redirigés avec un message par @require_active_company.
class AccountForm(forms.ModelForm):
 class Meta:
  model=LedgerAccount;fields=('code','name','kind')
  labels={'code':'Code','name':'Intitulé','kind':'Type'}
class EntryForm(forms.ModelForm):
 class Meta:
  model=JournalEntry;fields=('entry_date','description','debit_account','credit_account','amount')
  labels={'entry_date':'Date','description':'Libellé','debit_account':'Compte débité','credit_account':'Compte crédité','amount':'Montant'}
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);accounts=LedgerAccount.objects.filter(company=company,is_active=True);self.fields['debit_account'].queryset=accounts;self.fields['credit_account'].queryset=accounts
class TreasuryAccountForm(forms.ModelForm):
 class Meta:
  model=TreasuryAccount;fields=('name','kind','currency','opening_balance')
  labels={'name':'Nom du compte','kind':'Type','currency':'Devise','opening_balance':'Solde initial'}
class TreasuryMovementForm(forms.ModelForm):
 class Meta:
  model=TreasuryMovement;fields=('account','direction','movement_date','amount','description','reference')
  labels={'account':'Compte','direction':'Sens','movement_date':'Date','amount':'Montant','description':'Libellé','reference':'Référence'}
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);self.fields['account'].queryset=TreasuryAccount.objects.filter(company=company,is_active=True)
@login_required
@require_active_company
@permission_required('finance.view_ledgeraccount',raise_exception=True)
def accounting(request):
 enabled(request,'accounting');accounts=LedgerAccount.objects.filter(company=request.company);entries=JournalEntry.objects.filter(company=request.company).select_related('debit_account','credit_account')
 balances=[]
 for account in accounts:
  debits=sum((e.amount for e in entries if e.state==JournalEntry.State.POSTED and e.debit_account_id==account.pk),0)
  credits=sum((e.amount for e in entries if e.state==JournalEntry.State.POSTED and e.credit_account_id==account.pk),0)
  balances.append({'account':account,'debits':debits,'credits':credits,'balance':debits-credits})
 return render(request,'finance/accounting.html',{'accounts':accounts,'entries':entries[:100],'balances':balances,'account_form':AccountForm(),'entry_form':EntryForm(company=request.company)})
@login_required
@require_POST
@require_active_company
@permission_required('finance.add_ledgeraccount',raise_exception=True)
def create_account(request):
 enabled(request,'accounting');form=AccountForm(request.POST)
 if form.is_valid():
  account=form.save(commit=False);account.company=request.company
  try:account.full_clean();account.save()
  except ValidationError as ex:messages.error(request,str(ex))
  else:messages.success(request,'Compte créé.');return redirect('finance:accounting')
 messages.error(request,form.errors.as_text());return redirect('finance:accounting')
@login_required
@require_POST
@require_active_company
@permission_required('finance.add_journalentry',raise_exception=True)
def create_entry(request):
 enabled(request,'accounting');form=EntryForm(request.POST,company=request.company)
 if form.is_valid():
  entry=form.save(commit=False);entry.company=request.company;entry.created_by=request.user
  try:entry.full_clean();entry.save()
  except ValidationError as ex:messages.error(request,str(ex))
  else:messages.success(request,f'Écriture {entry.number} enregistrée en brouillon.');return redirect('finance:accounting')
 messages.error(request,form.errors.as_text());return redirect('finance:accounting')
@login_required
@require_POST
@require_active_company
@permission_required('finance.change_journalentry',raise_exception=True)
def post_entry(request,entry_id):
 enabled(request,'accounting')
 with transaction.atomic():
  entry=get_object_or_404(JournalEntry.objects.select_for_update(),pk=entry_id,company=request.company,state=JournalEntry.State.DRAFT)
  try:entry.full_clean()
  except ValidationError as ex:
   messages.error(request,'Écriture non comptabilisée : '+str(ex.messages[0]) if ex.messages else 'Écriture invalide.')
   return redirect('finance:accounting')
  entry.state=JournalEntry.State.POSTED;entry.save(update_fields=['state']);AuditLog.objects.create(actor=request.user,action='ACCOUNTING_POSTED',method='POST',path=request.path,status_code=200)
 return redirect('finance:accounting')
@login_required
@require_active_company
@permission_required('finance.view_treasuryaccount',raise_exception=True)
def treasury(request):
 enabled(request,'treasury');accounts=TreasuryAccount.objects.filter(company=request.company).prefetch_related('movements');movements=TreasuryMovement.objects.filter(company=request.company).select_related('account','created_by')[:100]
 return render(request,'finance/treasury.html',{'accounts':accounts,'movements':movements,'account_form':TreasuryAccountForm(),'movement_form':TreasuryMovementForm(company=request.company)})
@login_required
@require_POST
@require_active_company
@permission_required('finance.add_treasuryaccount',raise_exception=True)
def create_treasury_account(request):
 enabled(request,'treasury');form=TreasuryAccountForm(request.POST)
 if form.is_valid():
  account=form.save(commit=False);account.company=request.company
  try:account.full_clean();account.save()
  except ValidationError as ex:messages.error(request,str(ex))
  else:messages.success(request,'Compte de trésorerie créé.');return redirect('finance:treasury')
 messages.error(request,form.errors.as_text());return redirect('finance:treasury')
@login_required
@require_POST
@require_active_company
@permission_required('finance.add_treasurymovement',raise_exception=True)
def create_treasury_movement(request):
 enabled(request,'treasury');form=TreasuryMovementForm(request.POST,company=request.company)
 if form.is_valid():
  movement=form.save(commit=False);movement.company=request.company;movement.created_by=request.user
  try:
   movement.full_clean()
   with transaction.atomic():
    account=TreasuryAccount.objects.select_for_update().get(pk=movement.account_id,company=request.company)
    if movement.direction=='OUT' and movement.amount>account.balance:raise ValidationError({'amount':'Le solde du compte est insuffisant.'})
    movement.save()
  except ValidationError as ex:messages.error(request,str(ex))
  else:messages.success(request,'Mouvement de trésorerie enregistré.');return redirect('finance:treasury')
 messages.error(request,form.errors.as_text());return redirect('finance:treasury')
