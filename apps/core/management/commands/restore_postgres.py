import os
import shutil
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = "Restaure une sauvegarde PostgreSQL dans la base configurée (action destructive)."

    def add_arguments(self, parser):
        parser.add_argument("backup", help="Chemin du fichier .dump")
        parser.add_argument("--confirm", action="store_true", help="Confirme le remplacement des objets de la base cible.")

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError("Restauration destructive annulée. Vérifiez la base cible puis ajoutez --confirm.")
        backup = Path(options["backup"])
        if not backup.is_file():
            raise CommandError(f"Fichier de sauvegarde introuvable : {backup}")
        database = connections["default"].settings_dict
        if database["ENGINE"] != "django.db.backends.postgresql":
            raise CommandError("Cette commande nécessite PostgreSQL.")
        executable = shutil.which("pg_restore")
        if not executable:
            raise CommandError("pg_restore est introuvable. Installez les outils client PostgreSQL.")

        arguments = [executable, "--clean", "--if-exists", "--no-owner", "--exit-on-error", "--single-transaction"]
        for option, key in (("--host", "HOST"), ("--port", "PORT"), ("--username", "USER")):
            if database.get(key):
                arguments.extend((option, str(database[key])))
        arguments.extend(("--dbname", database["NAME"], str(backup)))
        environment = os.environ.copy()
        if database.get("PASSWORD"):
            environment["PGPASSWORD"] = database["PASSWORD"]
        try:
            subprocess.run(arguments, env=environment, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip() or "Erreur inconnue de pg_restore."
            raise CommandError(f"La restauration a échoué : {detail}") from error
        self.stdout.write(self.style.SUCCESS(f"Restauration terminée dans la base {database['NAME']}."))
