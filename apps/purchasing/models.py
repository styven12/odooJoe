from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT='DRAFT','Brouillon'
        ORDERED='ORDERED','Commandée'
        RECEIVED='RECEIVED','Réceptionnée'
        CANCELLED='CANCELLED','Annulée'
    number=models.CharField(max_length=24, unique=True, null=True, blank=True)
    company=models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='purchase_orders')
    supplier=models.ForeignKey('crm.Partner', on_delete=models.PROTECT, related_name='purchase_orders')
    product=models.ForeignKey('inventory.Product', on_delete=models.PROTECT, related_name='purchase_orders')
    quantity=models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost=models.DecimalField(max_digits=14, decimal_places=2)
    currency=models.CharField(max_length=3, default='XAF')
    status=models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    notes=models.TextField(blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='purchase_orders_created')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['-created_at']
        constraints=[models.CheckConstraint(condition=Q(quantity__gt=0), name='purchase_quantity_positive'), models.CheckConstraint(condition=Q(unit_cost__gte=0), name='purchase_cost_nonnegative')]
    @property
    def total(self): return self.quantity*self.unit_cost
    def clean(self):
        errors={}
        if self.supplier_id and self.company_id and self.supplier.company_id != self.company_id: errors['supplier']='Le fournisseur doit appartenir à la société active.'
        if self.product_id and self.company_id and self.product.company_id != self.company_id: errors['product']='L’article doit appartenir à la société active.'
        if self.supplier_id and self.supplier.partner_type not in ('SUPPLIER','BOTH'): errors['supplier']='Le contact sélectionné n’est pas un fournisseur.'
        if errors: raise ValidationError(errors)
    def save(self,*args,**kwargs):
        creating=self.pk is None
        super().save(*args,**kwargs)
        if creating and not self.number:
            self.number=f'PO-{timezone.localdate():%Y}-{self.pk:06d}'
            type(self).objects.filter(pk=self.pk).update(number=self.number)
    def __str__(self): return self.number or f'Achat #{self.pk}'
