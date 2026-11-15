from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
class BillOfMaterials(models.Model):
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='bills_of_materials')
 product=models.ForeignKey('inventory.Product',on_delete=models.PROTECT,related_name='bill_of_materials')
 component=models.ForeignKey('inventory.Product',on_delete=models.PROTECT,related_name='used_in_boms')
 quantity=models.DecimalField(max_digits=12,decimal_places=3)
 class Meta:
  constraints=[models.UniqueConstraint(fields=['product','component'],name='production_bom_product_component_unique'),models.CheckConstraint(condition=Q(quantity__gt=0),name='production_bom_qty_positive')]
 def clean(self):
  if self.product_id and self.component_id and self.product_id==self.component_id:raise ValidationError('Un produit ne peut pas être son propre composant.')
  if self.product_id and self.component_id and self.product.company_id!=self.component.company_id:raise ValidationError('Les composants doivent appartenir à la même société.')
 def __str__(self):return f'{self.product} ← {self.component} × {self.quantity}'
class ManufacturingOrder(models.Model):
 class State(models.TextChoices): DRAFT='DRAFT','Brouillon'; IN_PROGRESS='IN_PROGRESS','En cours'; DONE='DONE','Terminée'; CANCELLED='CANCELLED','Annulée'
 number=models.CharField(max_length=24,unique=True,null=True,blank=True)
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='manufacturing_orders')
 product=models.ForeignKey('inventory.Product',on_delete=models.PROTECT,related_name='manufacturing_orders')
 quantity=models.DecimalField(max_digits=12,decimal_places=3)
 state=models.CharField(max_length=12,choices=State.choices,default=State.DRAFT)
 created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:ordering=['-created_at'];constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name='production_order_qty_positive')]
 def save(self,*args,**kwargs):
  creating=self.pk is None;super().save(*args,**kwargs)
  if creating and not self.number:
   self.number=f'MO-{self.company_id}-{self.pk:06d}';type(self).objects.filter(pk=self.pk).update(number=self.number)
class Shipment(models.Model):
 class State(models.TextChoices): READY='READY','À préparer'; SHIPPED='SHIPPED','Expédiée'; DELIVERED='DELIVERED','Livrée'; CANCELLED='CANCELLED','Annulée'
 number=models.CharField(max_length=24,unique=True,null=True,blank=True)
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='shipments')
 order=models.ForeignKey('sales.SalesOrder',on_delete=models.PROTECT,related_name='shipments')
 product=models.ForeignKey('inventory.Product',on_delete=models.PROTECT,related_name='shipments')
 quantity=models.DecimalField(max_digits=12,decimal_places=3)
 carrier=models.CharField(max_length=120,blank=True)
 tracking_reference=models.CharField(max_length=120,blank=True)
 state=models.CharField(max_length=12,choices=State.choices,default=State.READY)
 created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:ordering=['-created_at'];constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name='production_shipment_qty_positive')]
 def clean(self):
  if self.order_id and self.company_id and self.order.company_id!=self.company_id:raise ValidationError({'order':'La commande doit appartenir à la société active.'})
  if self.product_id and self.company_id and self.product.company_id!=self.company_id:raise ValidationError({'product':'L’article doit appartenir à la société active.'})
 def save(self,*args,**kwargs):
  creating=self.pk is None;super().save(*args,**kwargs)
  if creating and not self.number:
   self.number=f'DEL-{self.company_id}-{self.pk:06d}';type(self).objects.filter(pk=self.pk).update(number=self.number)
