from .models import AuditLog

class AuditLogMiddleware:
    """
    Journalise les requêtes des utilisateurs authentifiés.
    En production, compléter ce journal par des événements métier explicites
    (validation de commande, modification de stock, paiement, etc.).
    """
    EXCLUDED_PREFIXES = ("/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path
        user = getattr(request, "user", None)

        if (
            user is not None
            and user.is_authenticated
            and not path.startswith(self.EXCLUDED_PREFIXES)
            and path != "/favicon.ico"
        ):
            ip = request.META.get("REMOTE_ADDR")
            AuditLog.objects.create(
                actor=user,
                method=request.method,
                path=path[:500],
                status_code=response.status_code,
                ip_address=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            )
        return response
