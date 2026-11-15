# Mini-Odoo — Phase 1 (Core Engine)

Socle initial Django/PostgreSQL : comptes, sociétés, catalogue des 22 modules, journal d'audit, tableau de bord et groupes de permissions.

## Déploiement sur Render (production)

Le projet est prêt pour Render : la configuration de production est intégrée dans `config/settings.py` (détection automatique de Render, base PostgreSQL préconfigurée, sécurité HTTPS, collectstatic et migrations automatiques). **Aucune variable d'environnement n'est obligatoire.**

### 1. Pousser le code sur GitHub
Envoyer le contenu de ce dossier dans le dépôt GitHub branché au service Render (ex. `styven12/odooJoe`). Le fichier `.env` est ignoré par git (`.gitignore`) : c'est normal et souhaité — la production n'en dépend pas.

### 2. Régler le service Render (Settings)
- **Build Command** : `bash build.sh`
- **Start Command** : `gunicorn config.wsgi:application` (inchangé)

Même si le Build Command n'est pas modifié, le service prépare lui-même sa base et ses fichiers statiques au démarrage (`config/wsgi.py`, `AUTO_SETUP=1` par défaut) ; il est toutefois recommandé d'utiliser `bash build.sh`.

Variables d'environnement optionnelles (Environment) :

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `PYTHON_VERSION` | `3.11.9` | Version Python (déjà définie) |
| `DATABASE_URL` | URL PostgreSQL Render intégrée | Base de données. **Ne pas définir avec une URL locale** (`127.0.0.1`/`localhost`) : sur Render elle est ignorée automatiquement (avertissement dans les logs). Pour la changer, n'utiliser que l'URL PostgreSQL Render (interne si même région). |
| `ADMIN_USERNAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `admin` / `admin@mini-odoo.local` / `MiniOdoo-4jjcLZJYCi` | Superutilisateur de secours créé uniquement sur une base neuve |
| `AUTO_SETUP` | `1` | Migrations + données initiales au démarrage (`0` pour désactiver) |
| `SECURE_SSL_REDIRECT` | `True` | Redirection HTTPS en production |

> **Important** : ne recopiez pas votre `.env` local dans les variables Render. Une `DATABASE_URL` du type `postgres://erp_user:...@127.0.0.1:5432/...` ne peut pas fonctionner sur Render (aucun PostgreSQL local dans le conteneur) et provoque des erreurs 500 dès qu'une page touche la base (connexion, sessions...). Le code la détecte et l'ignore désormais, mais le plus propre est de la supprimer du dashboard.

### 3. Première connexion
Sur une base neuve, un superutilisateur de secours est créé automatiquement :
- URL : `https://odoojoe.onrender.com`
- Identifiant : `admin`
- Mot de passe : `MiniOdoo-4jjcLZJYCi`

**Changez ce mot de passe immédiatement** (Administration → Utilisateurs) ou définissez `ADMIN_PASSWORD` avant le premier déploiement.

### 4. Ce qui est fait automatiquement à chaque déploiement
1. `collectstatic` : fichiers statiques (admin) servis par WhiteNoise, compression gzip/brotli.
2. `migrate` : schéma PostgreSQL à jour (idempotent).
3. `seed_modules` : catalogue des 22 modules métiers.
4. `setup_roles` : groupes Administrateur ERP, Manager ERP, Employé ERP.
5. `ensure_admin` : admin de secours si la base ne contient aucun utilisateur.
6. `seed_company` : société par défaut « Société principale » (code MAIN) + rattachement des superutilisateurs comme propriétaires. **Sans société active, la plupart des modules renvoyaient une 404** (« Société active requise ») : cette commande garantit que tout est utilisable immédiatement. Renommez la société dans l'administration Django (Sociétés) si besoin.

### 5. Robustesse sur base vide
Toutes les pages affichent un état vide utilisable et tous les formulaires sont protégés :
- GET sans société active : listes vides avec message, jamais de 404.
- POST sans société active : redirection vers le tableau de bord avec un message explicite, jamais de 500.
- Fichiers statiques : le stockage manifeste est tolérant (URL non hachée au pire cas) au lieu de planter.
- Erreurs HTTP habillées : 404, 403, 405, 500 et échec CSRF renvoient une vraie page Mini-Odoo avec navigation de secours (jamais de page blanche « Not Found »).
- Ressources navigateur : `/favicon.ico` (icône SVG) et `/robots.txt` sont servis — plus aucun 404 dans les logs à chaque visite.
- Disque éphémère : le téléchargement d'un document disparu du stockage redirige vers la bibliothèque avec un message clair au lieu d'un 404 brut.

La suite de tests couvre tous les scénarios : `python manage.py test` exécute 66 tests (unitaires + intégration incluant les parcours complets de chaque module sur base vide, le scénario « sans société », les pages d'erreur et la couverture dynamique de toutes les routes nommées).

### Notes importantes
- **Plan gratuit Render** : le service web se met en veille après ~15 minutes d'inactivité ; la première requête suivante peut prendre 30-60 s (redémarrage à froid). La base PostgreSQL gratuite expire après 30 jours et le disque est éphémère (fichiers uploadés perdus à chaque redéploiement). Pour la persistance, prévoir un stockage externe (S3, Cloudinary) ou un disque payant.
- **URL interne de la base** : si le service web est dans la même région que la base (Ohio), utiliser `DATABASE_URL` avec l'URL interne (`dpg-...-a/mini_odoo`) est plus rapide. L'URL externe (`.ohio-postgres.render.com`) utilisée par défaut fonctionne partout, avec SSL obligatoire (activé automatiquement).
- **Logs** : les erreurs applicatives s'affichent désormais dans les logs Render (config `LOGGING` ajoutée).
- Le journal d'audit trace les requêtes authentifiées ; la table `audit_auditlog` grossit avec le trafic.

## Prérequis (développement local)
- Windows 11
- Python 3.11+
- PostgreSQL installé et démarré
- PowerShell

## Installation
1. Créer et activer un environnement virtuel :
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Installer les dépendances :
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Copier `.env.example` vers `.env`, puis modifier `SECRET_KEY` et `DATABASE_URL`.
4. Dans pgAdmin ou psql, créer la base et l'utilisateur :
   ```sql
   CREATE USER erp_user WITH PASSWORD 'VotreMotDePasse';
   CREATE DATABASE mini_odoo_db OWNER erp_user;
   ```
5. Créer les migrations et migrer :
   ```powershell
   python manage.py makemigrations accounts companies core audit
   python manage.py migrate
   ```
6. Créer l'administrateur :
   ```powershell
   python manage.py createsuperuser
   ```
7. Initialiser le catalogue et les groupes :
   ```powershell
   python manage.py seed_modules
   python manage.py setup_roles
   ```
8. Démarrer :
   ```powershell
   python manage.py runserver
   ```
9. Ouvrir http://127.0.0.1:8000/ puis http://127.0.0.1:8000/admin/.

## Sécurité et périmètre
- Ne publiez jamais `.env` ni votre SECRET_KEY.
- Le compte superutilisateur Django sert à l'administration initiale.
- Les groupes sont une base RBAC de départ. L'isolation des données par société et les permissions fines par enregistrement seront ajoutées avant la mise en production.
- Le catalogue active/désactive l'accès fonctionnel à un module dans l'interface ; il ne charge/décharge pas les applications Django à chaud.
- Le journal actuel trace les requêtes authentifiées. Les événements métier sensibles devront être journalisés explicitement.
- Le CDN Tailwind est pratique pour le prototype. Pour la production, compiler et servir les assets localement.
