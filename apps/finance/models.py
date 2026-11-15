from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
class LedgerAccount(models.Model):
 class Kind(models.TextChoices): ASSET='ASSET','Actif'; LIABILITY='LIABILITY','Passif'; EQUITY='EQUITY','Capitaux propres'; INCOME='INCOME','Produit'; EXPENSE='EXPENSE','Charge'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='ledger_accounts')
 code=models.CharField(max_length=20)
 name=models.CharField(max_length=140)
 kind=models.CharField(max_length=12,choices=Kind.choices)
 is_active=models.BooleanField(default=True)
 class Meta:
  ordering=['code'];constraints=[models.UniqueConstraint(fields=['company','code'],name='finance_account_company_code_unique')]
 def __str__(self):return f'{self.code} · {self.name}'
class JournalEntry(models.Model):
 class State(models.TextChoices): DRAFT='DRAFT','Brouillon'; POSTED='POSTED','Comptabilisée'; VOID='VOID','Annulée'
 number=models.CharField(max_length=24,unique=True,null=True,blank=True)
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='journal_entries')
 entry_date=models.DateField(default=timezone.localdate)
 description=models.CharField(max_length=200)
 debit_account=models.ForeignKey(LedgerAccount,on_delete=models.PROTECT,related_name='debit_entries')
 credit_account=models.ForeignKey(LedgerAccount,on_delete=models.PROTECT,related_name='credit_entries')
 amount=models.DecimalField(max_digits=14,decimal_places=2)
 state=models.CharField(max_length=10,choices=State.choices,default=State.DRAFT)
 created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:
  ordering=['-entry_date','-created_at'];constraints=[models.CheckConstraint(condition=Q(amount__gt=0),name='finance_journal_amount_positive')]
 def clean(self):
  if self.debit_account_id and self.credit_account_id and self.debit_account_id==self.credit_account_id:raise ValidationError('Les comptes débit et crédit doivent être différents.')
  for field in ('debit_account','credit_account'):
   account=getattr(self,field,None)
   if account and self.company_id and account.company_id!=self.company_id:raise ValidationError({field:'Le compte doit appartenir à la société active.'})
 def save(self,*args,**kwargs):
  creating=self.pk is None;super().save(*args,**kwargs)
  if creating and not self.number:
   self.number=f'JRN-{self.company_id}-{self.pk:06d}';type(self).objects.filter(pk=self.pk).update(number=self.number)
class TreasuryAccount(models.Model):
 class Kind(models.TextChoices): BANK='BANK','Banque'; CASH='CASH','Caisse'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='treasury_accounts')
 name=models.CharField(max_length=140)
 kind=models.CharField(max_length=8,choices=Kind.choices)
 currency=models.CharField(max_length=3,default='XAF')
 opening_balance=models.DecimalField(max_digits=14,decimal_places=2,default=0)
 is_active=models.BooleanField(default=True)
 class Meta:ordering=['name']
 def __str__(self):return self.name
 @property
 def balance(self):
  from django.db.models import Sum,Case,When,F
  net=self.movements.aggregate(value=Sum(Case(When(direction='IN',then=F('amount')),default=-F('amount'))))['value'] or 0
  return self.opening_balance+net
class TreasuryMovement(models.Model):
 class Direction(models.TextChoices): IN='IN','Entrée'; OUT='OUT','Sortie'
 account=models.ForeignKey(TreasuryAccount,on_delete=models.PROTECT,related_name='movements')
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='treasury_movements')
 direction=models.CharField(max_length=3,choices=Direction.choices)
 movement_date=models.DateField(default=timezone.localdate)
 amount=models.DecimalField(max_digits=14,decimal_places=2)
 description=models.CharField(max_length=200)
 reference=models.CharField(max_length=100,blank=True)
 created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:ordering=['-movement_date','-created_at'];constraints=[models.CheckConstraint(condition=Q(amount__gt=0),name='finance_treasury_movement_positive')]
 def clean(self):
  if self.account_id and self.company_id and self.account.company_id!=self.company_id:raise ValidationError({'account':'Le compte doit appartenir à la société active.'})
