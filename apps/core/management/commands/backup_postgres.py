import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = "Crée une sauvegarde PostgreSQL au format custom dans backups/."

    def add_arguments(self, parser):
        parser.add_argument("--output", help="Chemin complet de la sauvegarde (facultatif).")

    def handle(self, *args, **options):
        connection = connections["default"]
        database = connection.settings_dict
        if database["ENGINE"] != "django.db.backends.postgresql":
            raise CommandError("Cette commande nécessite PostgreSQL.")
        executable = shutil.which("pg_dump")
        if not executable:
            raise CommandError("pg_dump est introuvable. Installez les outils client PostgreSQL.")

        target = Path(options["output"]) if options["output"] else (
            Path(settings.BASE_DIR) / "backups" / f"mini-odoo-{datetime.now().astimezone():%Y%m%d-%H%M%S-%f}.dump"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise CommandError(f"Le fichier existe déjà : {target}")
        partial = target.with_name(f".{target.name}.{os.getpid()}.partial")
        if partial.exists():
            raise CommandError(f"Un fichier temporaire existe déjà : {partial}")

        arguments = [executable, "--format=custom", "--no-owner", "--file", str(partial)]
        for option, key in (("--host", "HOST"), ("--port", "PORT"), ("--username", "USER")):
            if database.get(key):
                arguments.extend((option, str(database[key])))
        arguments.append(database["NAME"])
        environment = os.environ.copy()
        if database.get("PASSWORD"):
            environment["PGPASSWORD"] = database["PASSWORD"]

        try:
            subprocess.run(arguments, env=environment, check=True, capture_output=True, text=True)
            if target.exists():
                raise CommandError(f"Le fichier existe déjà : {target}")
            partial.rename(target)
        except CommandError:
            partial.unlink(missing_ok=True)
            raise
        except subprocess.CalledProcessError as error:
            partial.unlink(missing_ok=True)
            detail = error.stderr.strip() or "Erreur inconnue de pg_dump."
            raise CommandError(f"La sauvegarde a échoué : {detail}") from error
        except OSError as error:
            partial.unlink(missing_ok=True)
            raise CommandError(f"Impossible de finaliser la sauvegarde : {error}") from error
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {target} ({target.stat().st_size:,} octets)"))
