"""
Configuration Django du Mini-Odoo.

Fonctionnement :
- En LOCAL : le fichier .env est lu (DEBUG, SECRET_KEY, DATABASE_URL, ...).
- Sur RENDER : la configuration de production est appliquée automatiquement.
  Render expose les variables RENDER=true et RENDER_EXTERNAL_URL ; aucune
  variable d'environnement n'est donc requise pour déployer. La base
  PostgreSQL Render est préconfigurée ci-dessous (RENDER_DATABASE_URL) et
  peut être remplacée à tout moment par la variable d'environnement
  DATABASE_URL dans le tableau de bord Render.
"""
import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Mémorise les variables réellement définies dans l'environnement du process
# (dashboard Render, shell) AVANT la lecture du .env : sur Render, seul cet
# environnement réel doit primer, jamais un éventuel .env embarqué dans le dépôt.
_REAL_ENV_KEYS = set(os.environ.keys())

def _defined_in_real_env(name: str) -> bool:
    """True si la variable vient du vrai environnement (dashboard/shell)."""
    return name in _REAL_ENV_KEYS

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")  # silencieux si le fichier est absent

# ---------------------------------------------------------------------------
# Détection de l'environnement d'exécution
# ---------------------------------------------------------------------------
IS_RENDER = (
    os.environ.get("RENDER") == "true" or bool(os.environ.get("RENDER_EXTERNAL_URL"))
)
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")

# ---------------------------------------------------------------------------
# Sécurité : clé secrète et mode debug
# ---------------------------------------------------------------------------
if IS_RENDER:
    # Sur Render : clé du dashboard si définie, sinon clé de production
    # intégrée ; la valeur d'un .env embarqué est volontairement ignorée.
    SECRET_KEY = (
        os.environ["SECRET_KEY"]
        if _defined_in_real_env("SECRET_KEY")
        else "m3GezPPXOMLtsRgd7sytXNwEFjK1q53yRQtbZWtmJ2eXQr4GgU"
    )
else:
    SECRET_KEY = env("SECRET_KEY", default="unsafe-development-key-change-this")

# En local, DEBUG suit le .env (True par défaut). Sur Render, DEBUG est
# toujours False quelle que soit la valeur d'un éventuel .env embarqué.
DEBUG = env.bool("DEBUG", default=True) if not IS_RENDER else False

# ---------------------------------------------------------------------------
# Hôtes autorisés / CSRF
# ---------------------------------------------------------------------------
if IS_RENDER:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".onrender.com"]
    if RENDER_EXTERNAL_URL:
        from urllib.parse import urlsplit

        ALLOWED_HOSTS.append(urlsplit(RENDER_EXTERNAL_URL).hostname or "")
    ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if h]

    CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"]
    if RENDER_EXTERNAL_URL:
        CSRF_TRUSTED_ORIGINS.insert(0, RENDER_EXTERNAL_URL)
else:
    ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
    CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.companies",
    "apps.core",
    "apps.audit",
    "apps.crm",
    "apps.sales",
    "apps.inventory",
    "apps.purchasing",
    "apps.projects",
    "apps.people",
    "apps.service",
    "apps.production",
    "apps.documents",
    "apps.finance",
    "apps.retail",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.companies.middleware.ActiveCompanyMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.BrandedErrorPagesMiddleware",
    "apps.audit.middleware.AuditLogMiddleware",
]

ROOT_URLCONF = "config.urls"

# Page habillée quand la vérification CSRF échoue (session expirée, etc.).
CSRF_FAILURE_VIEW = "config.error_handlers.csrf_failure"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Base de données
# ---------------------------------------------------------------------------
# En local : valeur du .env (PostgreSQL local par défaut).
# Sur Render : la base PostgreSQL Render fournie ci-dessous est utilisée par
# défaut. Pour utiliser l'URL interne (plus rapide, même région uniquement)
# ou une autre base, définissez simplement DATABASE_URL dans le dashboard :
#   postgresql://mini_odoo_user:...@dpg-dbss7g1srm7s73aesd3g-a/mini_odoo
RENDER_DATABASE_URL = (
    "postgresql://mini_odoo_user:AoXcy47HrznMmqe6sDt84TxxFoJdBJLL"
    "@dpg-dbss7g1srm7s73aesd3g-a.ohio-postgres.render.com/mini_odoo"
)
LOCAL_DATABASE_URL = "postgres://erp_user:password@127.0.0.1:5432/mini_odoo_db"


def _db_url_is_local(url: str) -> bool:
    """True si l'URL pointe vers une base locale (127.0.0.1 / localhost)."""
    from urllib.parse import urlsplit

    host = (urlsplit(url).hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


if IS_RENDER:
    # Sur Render : URL du dashboard si définie, sinon la base Render
    # intégrée ; la valeur d'un .env embarqué est volontairement ignorée.
    _dashboard_db_url = (
        os.environ["DATABASE_URL"] if _defined_in_real_env("DATABASE_URL") else None
    )
    # Garde-fou : une URL de base locale (127.0.0.1 / localhost) ne peut pas
    # fonctionner sur Render (aucun PostgreSQL dans le conteneur). Elle est
    # ignorée au profit de la base PostgreSQL Render intégrée.
    if _dashboard_db_url and _db_url_is_local(_dashboard_db_url):
        print(
            f"[settings] ATTENTION : DATABASE_URL définie dans le dashboard Render "
            f"pointe vers une base locale ({_dashboard_db_url.split('@')[-1]}) : "
            "ignorée. Utilisation de la base PostgreSQL Render intégrée "
            "(RENDER_DATABASE_URL). Supprimez la variable DATABASE_URL du "
            "dashboard pour utiliser explicitement la base Render.",
            flush=True,
        )
        _database_url = RENDER_DATABASE_URL
    elif _dashboard_db_url:
        _database_url = _dashboard_db_url
    else:
        _database_url = RENDER_DATABASE_URL
else:
    _database_url = env("DATABASE_URL", default=LOCAL_DATABASE_URL)

DATABASES = {
    "default": env.db_url_config(_database_url),
}
DATABASES["default"]["CONN_MAX_AGE"] = 60
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# Connexion externe à PostgreSQL Render : SSL obligatoire.
if ".render.com" in _database_url and "sslmode" not in _database_url:
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["sslmode"] = "require"

# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
LANGUAGES = [
    ("fr", "Français"),
    ("en", "English"),
]
TIME_ZONE = env("TIME_ZONE", default="Africa/Douala")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Fichiers statiques et médias
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "config.storage.TolerantManifestStaticFilesStorage"},
}
# Tolérant aux entrées manquantes dans le manifest (évite les 500 si
# collectstatic n'a pas encore été exécuté).
WHITENOISE_MANIFEST_STRICT = False

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# ---------------------------------------------------------------------------
# Journaux : les erreurs s'affichent dans les logs Render (stdout)
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {"format": "[%(asctime)s] %(levelname)s %(name)s : %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Sécurité HTTP en production (appliquée dès que DEBUG est False)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
    SECURE_REFERRER_POLICY = "same-origin"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
