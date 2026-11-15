"""
Crée un superutilisateur de secours si la base ne contient encore aucun
utilisateur. Utilisé au déploiement Render (build.sh et auto-setup) pour
pouvoir se connecter dès la première mise en ligne sur une base neuve.

Identifiants par défaut (modifiables par variables d'environnement) :
  ADMIN_USERNAME (admin)
  ADMIN_EMAIL    (admin@mini-odoo.local)
  ADMIN_PASSWORD (MiniOdoo-4jjcLZJYCi)  -> à changer après la première connexion
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

DEFAULT_PASSWORD = "MiniOdoo-4jjcLZJYCi"


class Command(BaseCommand):
    help = (
        "Crée un superutilisateur de secours si aucun utilisateur n'existe encore "
        "(utile au premier déploiement sur une base neuve)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("ADMIN_USERNAME", "admin"))
        parser.add_argument(
            "--email", default=os.environ.get("ADMIN_EMAIL", "admin@mini-odoo.local")
        )
        parser.add_argument(
            "--password", default=os.environ.get("ADMIN_PASSWORD", DEFAULT_PASSWORD)
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if user_model.objects.exists():
            self.stdout.write(
                "Des utilisateurs existent déjà : aucun compte de secours créé."
            )
            return

        user_model.objects.create_superuser(
            username=username, email=email, password=password
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Superutilisateur « {username} » créé (mot de passe par défaut à "
                "changer dès la première connexion ou via la variable ADMIN_PASSWORD)."
            )
        )
