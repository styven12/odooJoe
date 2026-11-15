from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db.models import Q
class Command(BaseCommand):
    help = "Crée les groupes Administrateur ERP, Manager ERP et Employé ERP."

    def handle(self, *args, **options):
        all_permissions = Permission.objects.all()
        business_apps = ("companies", "crm", "sales", "inventory", "purchasing", "projects", "people", "service", "production", "documents", "finance", "retail")
        employee_apps = ("companies", "crm", "sales", "inventory", "purchasing", "projects", "people", "service", "production")
        manager_permissions = Permission.objects.filter(
            content_type__app_label__in=employee_apps,
        ).filter(
            Q(codename__startswith="view_")
            | Q(codename__startswith="add_")
            | Q(codename__startswith="change_")
        ) | Permission.objects.filter(content_type__app_label="sales", codename="confirm_salesorder")
        employee_permissions = Permission.objects.filter(
            content_type__app_label__in=business_apps,
            codename__startswith="view_",
        ) | Permission.objects.filter(content_type__app_label="core", codename="view_erpmodule") | Permission.objects.filter(
            content_type__app_label="audit", codename="view_auditlog"
        ) | Permission.objects.filter(content_type__app_label="people", codename__in=("add_leaverequest", "add_expensereport")) | Permission.objects.filter(content_type__app_label="service", codename="add_helpdeskticket") | Permission.objects.filter(content_type__app_label="retail", codename__in=("view_possession", "add_possession", "change_possession", "add_posreceipt"))

        definitions = {
            "Administrateur ERP": all_permissions,
            "Manager ERP": manager_permissions | Permission.objects.filter(content_type__app_label="core", codename="view_erpmodule") | Permission.objects.filter(
                content_type__app_label="audit", codename="view_auditlog"
            ),
            "Employé ERP": employee_permissions,
        }
        for name, permissions in definitions.items():
            group, _ = Group.objects.get_or_create(name=name)
            group.permissions.set(permissions.distinct())
            self.stdout.write(self.style.SUCCESS(f"Groupe configuré : {name}"))
        self.stdout.write(self.style.WARNING(
            "Attribuez les groupes ERP aux utilisateurs dans l'administration Django, puis vérifiez leur adhésion active aux sociétés autorisées."
        ))
