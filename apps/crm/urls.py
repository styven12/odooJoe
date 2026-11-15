from django.urls import path
from . import views

app_name = "crm"

urlpatterns = [
    path("opportunities/export.csv", views.export_opportunities, name="export_opportunities"),
    path("opportunities/new/", views.OpportunityCreateView.as_view(), name="opportunity_create"),
    path("", views.MonIndicateurView.as_view(), name="index"),
    path(
        "pipeline/",
        views.PipelineView.as_view(),
        name="pipeline"
    ),
]
