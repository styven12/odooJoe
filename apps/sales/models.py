from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class SalesOrder(models.Model):
    class State(models.TextChoices):
        QUOTATION = "QUOTATION", "Devis"
        CONFIRMED = "CONFIRMED", "Commande confirmée"
        CANCELLED = "CANCELLED", "Annulée"

    number = models.CharField(max_length=24, unique=True, null=True, blank=True)
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="sales_orders")
    customer = models.ForeignKey("crm.Partner", on_delete=models.PROTECT, related_name="sales_orders")
    opportunity = models.ForeignKey("crm.Opportunity", on_delete=models.PROTECT, related_name="sales_orders")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="XAF")
    state = models.CharField(max_length=16, choices=State.choices, default=State.QUOTATION)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sales_orders_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [("confirm_salesorder", "Can confirm a sales order")]
        constraints = [models.CheckConstraint(condition=Q(amount__gte=0), name="sales_order_amount_nonnegative")]

    def clean(self):
        errors = {}
        if self.customer_id and self.company_id and self.customer.company_id != self.company_id:
            errors["customer"] = "Le client doit appartenir à la même société que la commande."
        if self.opportunity_id and self.company_id and self.opportunity.company_id != self.company_id:
            errors["opportunity"] = "L’opportunité doit appartenir à la même société que la commande."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.number:
            self.number = f"QUO-{timezone.localdate():%Y}-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(number=self.number)

    def __str__(self):
        return self.number or f"Devis #{self.pk}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "À payer"
        PAID = "PAID", "Payée"
        VOID = "VOID", "Annulée"

    number = models.CharField(max_length=24, unique=True, null=True, blank=True)
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="invoices")
    sales_order = models.OneToOneField(SalesOrder, on_delete=models.PROTECT, related_name="invoice")
    customer = models.ForeignKey("crm.Partner", on_delete=models.PROTECT, related_name="invoices")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="XAF")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    issued_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="invoices_created")

    class Meta:
        ordering = ["-issued_at"]
        constraints = [models.CheckConstraint(condition=Q(amount__gte=0), name="invoice_amount_nonnegative")]

    def clean(self):
        errors = {}
        if self.sales_order_id and self.company_id and self.sales_order.company_id != self.company_id:
            errors["sales_order"] = "La commande doit appartenir à la même société que la facture."
        if self.customer_id and self.company_id and self.customer.company_id != self.company_id:
            errors["customer"] = "Le client doit appartenir à la même société que la facture."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.number:
            self.number = f"INV-{timezone.localdate():%Y}-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(number=self.number)

    def __str__(self):
        return self.number or f"Facture #{self.pk}"
