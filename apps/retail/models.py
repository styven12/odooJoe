from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
class RetailProduct(models.Model):
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='retail_products')
 product=models.OneToOneField('inventory.Product',on_delete=models.PROTECT,related_name='retail_listing')
 price=models.DecimalField(max_digits=14,decimal_places=2)
 active=models.BooleanField(default=True)
 online=models.BooleanField(default=False)
 class Meta:constraints=[models.CheckConstraint(condition=Q(price__gte=0),name='retail_price_nonnegative')]
 def __str__(self):return self.product.name
class POSSession(models.Model):
 class State(models.TextChoices): OPEN='OPEN','Ouverte'; CLOSED='CLOSED','Clôturée'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='pos_sessions')
 opened_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='pos_sessions_opened')
 opened_at=models.DateTimeField(auto_now_add=True)
 opening_cash=models.DecimalField(max_digits=14,decimal_places=2,default=0)
 state=models.CharField(max_length=8,choices=State.choices,default=State.OPEN)
 closed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='pos_sessions_closed')
 closed_at=models.DateTimeField(null=True,blank=True)
 closing_cash=models.DecimalField(max_digits=14,decimal_places=2,null=True,blank=True)
 class Meta:
  ordering=['-opened_at']
  constraints=[models.UniqueConstraint(fields=['company'],condition=Q(state='OPEN'),name='retail_one_open_session_per_company'),models.CheckConstraint(condition=Q(opening_cash__gte=0),name='retail_opening_cash_nonnegative')]
 @property
 def expected_cash(self):
  return self.opening_cash+sum((r.total for r in self.receipts.filter(payment_method='CASH')),0)
class POSReceipt(models.Model):
 class Payment(models.TextChoices): CASH='CASH','Espèces'; MOBILE='MOBILE','Mobile money'; CARD='CARD','Carte'
 number=models.CharField(max_length=24,unique=True,null=True,blank=True)
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='pos_receipts')
 session=models.ForeignKey(POSSession,on_delete=models.PROTECT,related_name='receipts')
 product=models.ForeignKey('inventory.Product',on_delete=models.PROTECT,related_name='pos_receipts')
 quantity=models.DecimalField(max_digits=12,decimal_places=3)
 unit_price=models.DecimalField(max_digits=14,decimal_places=2)
 payment_method=models.CharField(max_length=8,choices=Payment.choices)
 payment_reference=models.CharField(max_length=100,blank=True)
 customer_name=models.CharField(max_length=160,blank=True)
 created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:ordering=['-created_at'];constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name='retail_pos_qty_positive'),models.CheckConstraint(condition=Q(unit_price__gte=0),name='retail_pos_price_nonnegative')]
 @property
 def total(self):return self.quantity*self.unit_price
 def save(self,*args,**kwargs):
  creating=self.pk is None;super().save(*args,**kwargs)
  if creating and not self.number:
   self.number=f'POS-{self.company_id}-{self.pk:06d}';type(self).objects.filter(pk=self.pk).update(number=self.number)
class WebOrder(models.Model):
 class State(models.TextChoices): PENDING='PENDING','À confirmer'; CONFIRMED='CONFIRMED','Confirmée'; CANCELLED='CANCELLED','Annulée'
 number=models.CharField(max_length=24,unique=True,null=True,blank=True)
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='web_orders')
 customer=models.ForeignKey('crm.Partner',on_delete=models.PROTECT,related_name='web_orders')
 product=models.ForeignKey('inventory.Product',on_delete=models.PROTECT,related_name='web_orders')
 quantity=models.DecimalField(max_digits=12,decimal_places=3)
 unit_price=models.DecimalField(max_digits=14,decimal_places=2)
 state=models.CharField(max_length=10,choices=State.choices,default=State.PENDING)
 created_at=models.DateTimeField(auto_now_add=True)
 confirmed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
 class Meta:ordering=['-created_at'];constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name='retail_web_qty_positive'),models.CheckConstraint(condition=Q(unit_price__gte=0),name='retail_web_price_nonnegative')]
 @property
 def total(self):return self.quantity*self.unit_price
 def clean(self):
  if self.customer_id and self.company_id and self.customer.company_id!=self.company_id:raise ValidationError({'customer':'Le client doit appartenir à la société active.'})
  if self.product_id and self.company_id and self.product.company_id!=self.company_id:raise ValidationError({'product':'Le produit doit appartenir à la société active.'})
 def save(self,*args,**kwargs):
  creating=self.pk is None;super().save(*args,**kwargs)
  if creating and not self.number:
   self.number=f'WEB-{self.company_id}-{self.pk:06d}';type(self).objects.filter(pk=self.pk).update(number=self.number)
