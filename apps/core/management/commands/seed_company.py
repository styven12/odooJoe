"""
Crée la société par défaut du Mini-Odoo et rattache les superutilisateurs.

Sans société active, la plupart des modules affichaient une erreur 404
(« Société active requise ») et les formulaires de création plantaient. Cette
commande garantit qu'au moins une société existe et que les administrateurs y
sont rattachés. Elle est idempotente : sans effet si la société existe déjà.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.companies.models import Company, CompanyMembership

DEFAULT_CODE = "MAIN"


class Command(BaseCommand):
    help = (
        "Crée la société par défaut (code MAIN) si elle n'existe pas et rattache "
        "tous les superutilisateurs sans société comme propriétaires."
    )

    def handle(self, *args, **options):
        company, created = Company.objects.get_or_create(
            code=DEFAULT_CODE,
            defaults={
                "name": "Société principale",
                "country": "Cameroun",
                "currency": "XAF",
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Société par défaut créée : {company}"))
        else:
            self.stdout.write(f"Société par défaut déjà présente : {company}")

        user_model = get_user_model()
        attached = 0
        for user in user_model.objects.filter(is_superuser=True):
            _, membership_created = CompanyMembership.objects.get_or_create(
                company=company,
                user=user,
                defaults={"role": CompanyMembership.Role.OWNER, "is_active": True},
            )
            if membership_created:
                attached += 1
                self.stdout.write(f"  Rattaché : {user.username} (Propriétaire)")
        self.stdout.write(
            self.style.SUCCESS(f"{attached} superutilisateur(s) rattaché(s) à la société par défaut.")
        )
