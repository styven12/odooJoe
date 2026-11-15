from django.conf import settings
from django.db import models
from django.db.models import Q

class Product(models.Model):
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='products')
    sku = models.CharField(max_length=40)
    name = models.CharField(max_length=180)
    unit = models.CharField(max_length=24, default='unité')
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['name']
        constraints = [models.UniqueConstraint(fields=['company','sku'], name='inventory_company_sku_unique'), models.CheckConstraint(condition=Q(reorder_level__gte=0), name='inventory_reorder_nonnegative')]
    def __str__(self): return f'{self.sku} · {self.name}'
    @property
    def on_hand(self):
        from django.db.models import Sum, Case, When, F, DecimalField
        return self.movements.aggregate(total=Sum(Case(When(kind='IN', then=F('quantity')), default=-F('quantity'), output_field=DecimalField())))['total'] or 0

class StockMovement(models.Model):
    class Kind(models.TextChoices):
        IN='IN','Entrée'
        OUT='OUT','Sortie'
    company = models.ForeignKey('companies.Company', on_delete=models.PROTECT, related_name='stock_movements')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    kind = models.CharField(max_length=8, choices=Kind.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    reference = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']
        constraints=[models.CheckConstraint(condition=Q(quantity__gt=0), name='inventory_movement_positive')]
    def __str__(self): return f'{self.get_kind_display()} {self.product} × {self.quantity}'
