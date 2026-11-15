"""
Middleware d'habillage des erreurs HTTP du Mini-Odoo.

Certaines réponses sont produites par Django sous forme de texte brut ou de
page générique :
  - 405 « Method Not Allowed » quand une route POST-only est ouverte en GET ;
  - 403 « HttpResponseForbidden » renvoyé directement par une vue ;
  - 404 renvoyé sans passer par Http404 (ex. fichiers médias manquants).

Ce middleware remplace le corps de ces réponses par les pages habillées de
l'application, sans changer le code d'état HTTP. Les chemins /static/,
/media/ et /admin/ sont exclus (contenus binaires et administration Django).
"""
from django.template import loader

BRANDED_TEMPLATES = {
    403: "errors/403.html",
    404: "errors/404.html",
    405: "errors/405.html",
}
EXCLUDED_PREFIXES = ("/static/", "/media/", "/admin/")


class BrandedErrorPagesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        status = getattr(response, "status_code", None)
        template_name = BRANDED_TEMPLATES.get(status)
        if not template_name:
            return response
        if request.path.startswith(EXCLUDED_PREFIXES):
            return response
        body = response.content if hasattr(response, "content") else b""
        if b"<html" in body[:1024].lower() or b"<!doctype html" in body[:1024].lower():
            # Réponse déjà rendue comme page complète (handlers Django ou
            # vues qui construisent elles-mêmes une vraie page) : on ne
            # touche pas au contenu.
            return response
        try:
            html = loader.render_to_string(template_name, {"error_message": ""})
        except Exception:
            return response
        response.content = html.encode(response.charset or "utf-8")
        response["Content-Type"] = "text/html; charset=utf-8"
        return response
