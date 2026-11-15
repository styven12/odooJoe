"""
Garde-fous partagés des vues du Mini-Odoo.
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

COMPANY_MISSING_MESSAGE = (
    "Aucune société active n'est associée à votre compte. Une société par "
    "défaut peut être créée via la commande « python manage.py seed_company » "
    "ou dans l'administration Django (Sociétés)."
)


def require_active_company(view):
    """
    Empêche tout crash (IntegrityError / AttributeError) sur les requêtes POST
    lorsqu'aucune société active n'est associée à l'utilisateur : redirige vers
    le tableau de bord avec un message explicite. Les requêtes GET passent
    (les pages de liste affichent alors un état vide).
    """
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method == "POST" and not getattr(request, "company", None):
            messages.error(request, COMPANY_MISSING_MESSAGE)
            return redirect("dashboard")
        return view(request, *args, **kwargs)

    return wrapped
