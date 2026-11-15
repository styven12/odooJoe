"""
Gestionnaires d'erreurs HTTP personnalisés du Mini-Odoo.

Chaque erreur (404, 403, 405, 500, CSRF) renvoie une vraie page dans
l'interface de l'application, avec navigation de secours — jamais une page
blanche « Not Found » sans résultat. Les pages 404/403 conservent le code
d'état HTTP exact ; seul le corps est personnalisé.
"""
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render


def _message(exception):
    """Message lisible de l'exception, sans détail technique interne."""
    if exception is None:
        return ""
    text = str(exception).strip()
    return text


def error_404(request, exception=None):
    """Page « introuvable » avec la raison métier (ex. module désactivé)."""
    return render(
        request,
        "errors/404.html",
        {"error_message": _message(exception)},
        status=404,
    )


def error_403(request, exception=None):
    """Page « accès refusé » (permissions insuffisantes)."""
    return render(
        request,
        "errors/403.html",
        {"error_message": _message(exception)},
        status=403,
    )


def error_500(request):
    """Page « erreur interne » autonome : aucun accès base ni session."""
    return HttpResponse(
        loader.render_to_string("errors/500.html"),
        status=500,
        content_type="text/html; charset=utf-8",
    )


def csrf_failure(request, reason=""):
    """Échec de vérification CSRF : page explicite au lieu de la page brute."""
    return HttpResponse(
        loader.render_to_string("errors/403_csrf.html"),
        status=403,
        content_type="text/html; charset=utf-8",
    )
