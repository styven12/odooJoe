from django.conf import settings
from django.db import models

class Company(models.Model):
    name = models.CharField("raison sociale", max_length=180)
    code = models.CharField("code société", max_length=30, unique=True)
    tax_id = models.CharField("identifiant fiscal", max_length=80, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Cameroun")
    currency = models.CharField(max_length=3, default="XAF")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "société"
        verbose_name_plural = "sociétés"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class CompanyMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Propriétaire"
        MANAGER = "MANAGER", "Manager"
        EMPLOYEE = "EMPLOYEE", "Employé"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "affectation à une société"
        verbose_name_plural = "affectations aux sociétés"
        constraints = [
            models.UniqueConstraint(fields=["company", "user"], name="unique_company_user_membership")
        ]

    def __str__(self):
        return f"{self.user} — {self.company} ({self.get_role_display()})"
