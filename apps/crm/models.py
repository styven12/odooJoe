
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


# ==========================================================
# 1. PARTNER : CONTACTS ET PARTENAIRES
# ==========================================================

class Partner(models.Model):

    class PartnerType(models.TextChoices):
        LEAD = "LEAD", "Prospect"
        CUSTOMER = "CUSTOMER", "Client"
        BOTH = "BOTH", "Prospect et client"
        SUPPLIER = "SUPPLIER", "Fournisseur"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="crm_partners"
    )

    name = models.CharField(
        "Nom / Raison sociale",
        max_length=180
    )

    partner_type = models.CharField(
        "Type de partenaire",
        max_length=20,
        choices=PartnerType.choices,
        default=PartnerType.LEAD
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_crm_partners"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Partenaire"
        verbose_name_plural = "Partenaires"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["company", "email"],
                condition=~Q(email=""),
                name="crm_unique_partner_email"
            )
        ]

    def __str__(self):
        return self.name


# ==========================================================
# 2. LEAD : PROSPECTS COMMERCIAUX
# ==========================================================

class Lead(models.Model):

    class Status(models.TextChoices):
        NEW = "NEW", "Nouveau"
        CONTACTED = "CONTACTED", "Contacté"
        QUALIFIED = "QUALIFIED", "Qualifié"
        CONVERTED = "CONVERTED", "Converti"
        LOST = "LOST", "Perdu"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="crm_leads"
    )

    title = models.CharField(
        "Sujet du prospect",
        max_length=180
    )

    partner = models.ForeignKey(
        Partner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads"
    )

    contact_name = models.CharField(
        max_length=150,
        blank=True
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    source = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_crm_leads"
    )

    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_crm_leads"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prospect"
        verbose_name_plural = "Prospects"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.partner_id and self.company_id:
            if self.partner.company_id != self.company_id:
                raise ValidationError({
                    "partner": "Le contact doit appartenir à la même société."
                })


# ==========================================================
# 3. OPPORTUNITY : OPPORTUNITES COMMERCIALES
# ==========================================================

class Opportunity(models.Model):

    class Stage(models.TextChoices):
        NEW = "NEW", "Nouveau"
        QUALIFICATION = "QUALIFICATION", "Qualification"
        PROPOSAL = "PROPOSAL", "Proposition"
        NEGOTIATION = "NEGOTIATION", "Négociation"
        WON = "WON", "Gagné"
        LOST = "LOST", "Perdu"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="crm_opportunities"
    )

    name = models.CharField(
        "Nom de l'opportunité",
        max_length=180
    )

    partner = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name="opportunities"
    )

    lead = models.OneToOneField(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunity"
    )

    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.NEW
    )

    expected_revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    probability = models.PositiveSmallIntegerField(
        default=10
    )

    expected_closing_date = models.DateField(
        null=True,
        blank=True
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_opportunities"
    )

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Opportunité"
        verbose_name_plural = "Opportunités"
        ordering = ["-updated_at"]

        constraints = [
            models.CheckConstraint(
                condition=Q(probability__gte=0, probability__lte=100),
                name="crm_probability_between_0_100"
            ),
            models.CheckConstraint(
                condition=Q(expected_revenue__gte=0),
                name="crm_revenue_non_negative"
            )
        ]

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        if self.partner_id and self.company_id:
            if self.partner.company_id != self.company_id:
                errors["partner"] = (
                    "Le partenaire doit appartenir à la même société."
                )

        if self.lead_id and self.company_id:
            if self.lead.company_id != self.company_id:
                errors["lead"] = (
                    "Le prospect doit appartenir à la même société."
                )

        if errors:
            raise ValidationError(errors)


# ==========================================================
# 4. ACTIVITY : ACTIVITES COMMERCIALES
# ==========================================================

class Activity(models.Model):

    class ActivityType(models.TextChoices):
        CALL = "CALL", "Appel"
        MEETING = "MEETING", "Réunion"
        EMAIL = "EMAIL", "E-mail"
        TASK = "TASK", "Tâche"
        FOLLOWUP = "FOLLOWUP", "Relance"

    class Status(models.TextChoices):
        TODO = "TODO", "À faire"
        DONE = "DONE", "Terminée"
        CANCELLED = "CANCELLED", "Annulée"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="crm_activities"
    )

    title = models.CharField(max_length=180)

    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        default=ActivityType.TASK
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO
    )

    due_at = models.DateTimeField(
        default=timezone.now
    )

    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities"
    )

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities"
    )

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities"
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crm_activities"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_crm_activities"
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Activité commerciale"
        verbose_name_plural = "Activités commerciales"
        ordering = ["status", "due_at"]

    def __str__(self):
        return self.title

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        if self.partner_id and self.company_id:
            if self.partner.company_id != self.company_id:
                errors["partner"] = "Société du contact incorrecte."

        if self.lead_id and self.company_id:
            if self.lead.company_id != self.company_id:
                errors["lead"] = "Société du prospect incorrecte."

        if self.opportunity_id and self.company_id:
            if self.opportunity.company_id != self.company_id:
                errors["opportunity"] = "Société de l'opportunité incorrecte."

        if errors:
            raise ValidationError(errors)
