from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView
from django.views.static import serve as media_serve
from apps.core import views as core_views
from apps.companies import views as company_views

# Gestionnaires d'erreurs habillés (404/403/500 + CSRF).
handler403 = "config.error_handlers.error_403"
handler404 = "config.error_handlers.error_404"
handler500 = "config.error_handlers.error_500"

_static_prefix = "/" + settings.STATIC_URL.lstrip("/")

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("companies/active/", company_views.select_company, name="select_company"),
    path("sales/", include("apps.sales.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("purchasing/", include("apps.purchasing.urls")),
    path("projects/", include("apps.projects.urls")),
    path("hr/", include("apps.people.urls")),
    path("service/", include("apps.service.urls")),
    path("operations/", include("apps.production.urls")),
    path("documents/", include("apps.documents.urls")),
    path("finance/", include("apps.finance.urls")),
    path("retail/", include("apps.retail.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", core_views.dashboard, name="dashboard"),
    path("modules/", core_views.module_list, name="module_list"),
    path("modules/<slug:slug>/toggle/", core_views.toggle_module, name="toggle_module"),
    path("crm/", include("apps.crm.urls")), # Vérifiez que cette ligne pointe bien vers apps.crm.urls et non config.urls
    #path("crm/", include("apps.crm.urls")),
]

# Fichiers médias (uploads, ex. module documents) servis aussi en production.
# NB : le disque Render est éphémère en plan gratuit ; prévoir un stockage
# externe (S3, Cloudinary...) pour la persistance des fichiers.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT}),
]

# Ressources attendues par les navigateurs : favicon (icône d'onglet) et
# directives robots. Sans ces routes, chaque visite journalisait un 404.
urlpatterns += [
    path(
        "favicon.ico",
        RedirectView.as_view(url=f"{_static_prefix}favicon.svg", permanent=False),
        name="favicon",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
]
