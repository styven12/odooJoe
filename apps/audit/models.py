from django.conf import settings
from django.db import models

class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=30, default="HTTP_REQUEST")
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "événement d'audit"
        verbose_name_plural = "événements d'audit"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.actor or 'Anonyme'} — {self.method} {self.path}"
