"""
Configuration gunicorn chargée automatiquement (gunicorn lit
./gunicorn.conf.py par défaut), sans modifier la commande de démarrage Render.

- timeout élargi : la première exécution des migrations sur une base neuve
  peut dépasser les 30 secondes par défaut.
- threads : permet de servir plusieurs requêtes simultanées avec un seul
  worker (adapté aux instances gratuites Render).
- logs : access/error logs sur stdout, visibles dans la console Render.
"""
import os

wsgi_app = "config.wsgi:application"

workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
worker_class = "gthread"
threads = int(os.environ.get("WEB_THREADS", "4"))

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "180"))
graceful_timeout = 30
keepalive = 5

max_requests = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog = "-"
loglevel = "info"
