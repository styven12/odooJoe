from django.db import models

class ERPModule(models.Model):
    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_core = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=False)
    version = models.CharField(max_length=20, default="1.0.0")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "module ERP"
        verbose_name_plural = "modules ERP"
        ordering = ["name"]

    def __str__(self):
        return self.name
