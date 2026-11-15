# Exploitation de Mini-Odoo

## Modules réellement disponibles

Le CRM permet de consulter les contacts et opportunités, de créer une opportunité et d'exporter le pipeline. Le parcours Ventes / Facturation permet de transformer une opportunité en devis, de confirmer une commande, de créer sa facture, de marquer celle-ci payée et d'exporter les listes en CSV. Les autres entrées restent des aperçus de catalogue et ne peuvent pas être activées tant que leurs fonctions métier ne sont pas livrées.

Après installation ou mise à jour, appliquer les migrations et synchroniser les rôles et le catalogue :

```powershell
python manage.py migrate
python manage.py setup_roles
python manage.py seed_modules
```

Les utilisateurs doivent être membres de la société concernée. Les responsables peuvent accéder aux fonctions d'écriture ; les employés disposent de droits de consultation. Le superutilisateur peut sélectionner toute société active.

## Sauvegarder PostgreSQL

Installer les outils client PostgreSQL (`pg_dump`), puis lancer :

```powershell
python manage.py backup_postgres
```

La sauvegarde au format PostgreSQL custom est déposée dans `backups/`, exclu du contrôle de version. Elle contient des données d'entreprise : stockez une copie hors du poste, limitez son accès et vérifiez régulièrement qu'une restauration fonctionne.

Pour écrire à un autre emplacement :

```powershell
python manage.py backup_postgres --output "D:\Sauvegardes\mini-odoo.dump"
```

Restaurer dans une base de test avant toute récupération en production :

```powershell
python manage.py restore_postgres "D:\Sauvegardes\mini-odoo.dump" --confirm
```

La commande refuse de démarrer sans `--confirm`. Elle utilise la base configurée dans `.env` et remplace les objets homonymes. Vérifiez la cible et faites-en une sauvegarde préalable avant de l'utiliser.

## Mise en production

Copier `.env.example` vers `.env`, remplacer la clé secrète et les identifiants de base, fixer `DEBUG=False`, renseigner `ALLOWED_HOSTS`, puis déployer derrière HTTPS. Le paramètre `SECURE_SSL_REDIRECT=True` suppose que le proxy transmet `X-Forwarded-Proto: https`. Ne déployez pas les identifiants de démonstration (`root` / `root`) ; attribuez un mot de passe fort au compte administrateur et limitez l'accès à `/admin/`.

Avant une livraison, lancer `python manage.py check --deploy` et vérifier la procédure de restauration sur une base isolée.
