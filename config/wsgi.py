"""
Point d'entrée WSGI.

Sur Render, ce module prépare automatiquement l'application au démarrage :
migrations, fichiers statiques, catalogue des modules, groupes et
superutilisateur de secours. Ainsi, le déploiement fonctionne sans aucune
variable d'environnement à configurer, même si la commande de build n'a pas
été modifiée dans le tableau de bord. Ce préparation est idempotente : elle
ne modifie aucune donnée si elle a déjà été exécutée (par build.sh).
"""
import os
import subprocess
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def _auto_setup_on_render():
    """Prépare la base et les assets au premier démarrage sur Render."""
    is_render = (
        os.environ.get("RENDER") == "true" or bool(os.environ.get("RENDER_EXTERNAL_URL"))
    )
    auto_setup = os.environ.get("AUTO_SETUP", "1").strip().lower()
    if not is_render or auto_setup in {"0", "false", "no", "off"}:
        return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manage_py = os.path.join(base_dir, "manage.py")
    commands = [
        ["migrate", "--noinput"],
        ["collectstatic", "--noinput"],
        ["seed_modules"],
        ["setup_roles"],
        ["ensure_admin"],
        ["seed_company"],
    ]
    for cmd in commands:
        print(f"[auto-setup] python manage.py {' '.join(cmd)} ...", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, manage_py, *cmd],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=150,
            )
            if result.stdout.strip():
                print(result.stdout.strip(), flush=True)
            if result.returncode != 0:
                print(result.stderr.strip(), flush=True)
                print(
                    f"[auto-setup] ÉCHEC de « {' '.join(cmd)} » (code {result.returncode}), "
                    "le service démarre malgré tout.",
                    flush=True,
                )
        except Exception as exc:  # n'empêche jamais le serveur de démarrer
            print(f"[auto-setup] erreur : {exc}", flush=True)
    print("[auto-setup] terminé.", flush=True)


# IMPORTANT : l'auto-setup s'exécute AVANT la création de l'application WSGI,
# pour que WhiteNoise voie les fichiers statiques collectés (sinon index vide).
_auto_setup_on_render()

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
