#!/usr/bin/env bash
# Script de build Render.
# À renseigner dans le tableau de bord Render :
#   Build Command : bash build.sh
#   Start Command : gunicorn config.wsgi:application   (inchangé)
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Installation des dépendances"
pip install -r requirements.txt

echo "==> Collecte des fichiers statiques (collectstatic)"
python manage.py collectstatic --noinput

echo "==> Migrations de la base de données"
python manage.py migrate --noinput

echo "==> Données initiales : catalogue des modules, groupes, société, admin de secours"
python manage.py seed_modules
python manage.py setup_roles
python manage.py ensure_admin
python manage.py seed_company

echo "==> Build terminé avec succès"
