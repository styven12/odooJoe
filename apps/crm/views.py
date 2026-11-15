
from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum, Value
from django.shortcuts import redirect
from django.views.generic import CreateView, TemplateView
from django.contrib import messages
from django.urls import reverse_lazy
from django import forms
from django.http import Http404
from functools import wraps

from .models import Activity, Lead, Opportunity, Partner


def crm_module_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        from apps.core.models import ERPModule
        if not ERPModule.objects.filter(slug="crm", is_enabled=True).exists():
            raise Http404("Le module CRM est désactivé.")
        return view(request, *args, **kwargs)
    return wrapped


@login_required
@crm_module_required
@permission_required("crm.view_opportunity", raise_exception=True)
def export_opportunities(request):
    import csv
    from django.http import HttpResponse
    opportunities = Opportunity.objects.filter(company=request.company).select_related("partner", "assigned_to") if request.company else Opportunity.objects.none()
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="opportunites.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(("Opportunité", "Client", "Étape", "Montant attendu", "Probabilité", "Date prévue", "Responsable"))
    for opportunity in opportunities:
        row = (opportunity.name, opportunity.partner.name, opportunity.get_stage_display(), opportunity.expected_revenue, opportunity.probability, opportunity.expected_closing_date or "", opportunity.assigned_to or "")
        writer.writerow([("'" + value) if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value for value in row])
    return response


class MonIndicateurView(LoginRequiredMixin, TemplateView):
    template_name = "crm/index.html"
    permission_required = ("crm.view_partner", "crm.view_lead", "crm.view_opportunity", "crm.view_activity")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        from apps.core.models import ERPModule
        if not ERPModule.objects.filter(slug="crm", is_enabled=True).exists():
            raise Http404("Le module CRM est désactivé.")
        if not request.user.has_perms(self.permission_required):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Récupérer l'entreprise active de l'utilisateur
        # À adapter selon le mécanisme de sélection d'entreprise
        company = self.request.company

        partners = Partner.objects.filter(company=company) if company else Partner.objects.none()
        leads = Lead.objects.filter(company=company) if company else Lead.objects.none()
        opportunities = Opportunity.objects.filter(company=company) if company else Opportunity.objects.none()
        activities = Activity.objects.filter(company=company) if company else Activity.objects.none()

        if company:
            partners = partners.filter(company=company)
            leads = leads.filter(company=company)
            opportunities = opportunities.filter(company=company)
            activities = activities.filter(company=company)

        open_stages = [
            stage
            for stage, _ in Opportunity.Stage.choices
            if stage not in (Opportunity.Stage.WON, Opportunity.Stage.LOST)
        ]
        forecast = opportunities.filter(stage__in=open_stages).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("expected_revenue") * F("probability") / Value(100),
                    output_field=DecimalField(max_digits=16, decimal_places=2),
                )
            )
        )["total"]

        context["indicators"] = {
            "contacts": partners.count(),
            "prospects": leads.count(),
            "opportunites": opportunities.count(),
            "activites": activities.count(),
            "chiffre_affaires_previsionnel": forecast or Decimal("0"),
        }

        stage_counts = dict(
            opportunities.values("stage")
            .annotate(total=Count("id"))
            .values_list("stage", "total")
        )
        context["opportunities_by_stage"] = [
            {
                "stage": stage_value,
                "label": stage_label,
                "total": stage_counts.get(stage_value, 0),
            }
            for stage_value, stage_label in Opportunity.Stage.choices
            if stage_counts.get(stage_value, 0)
        ]

        # Afficher les activités créées le plus récemment.
        context["recent_activities"] = (
            activities.select_related(
                "partner", "lead", "opportunity", "assigned_to"
            )
            .order_by("-created_at")[:5]
        )

        # Pipeline commercial : une colonne par étape
        context["pipeline_columns"] = [
            {
                "value": stage_value,
                "label": stage_label,
                "opportunities": opportunities.filter(
                    stage=stage_value
                ).select_related("partner", "assigned_to"),
            }
            for stage_value, stage_label in Opportunity.Stage.choices
        ]


        return context


class PipelineView(MonIndicateurView):
    template_name = "crm/pipeline.html"


class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = ("name", "partner", "stage", "expected_revenue", "probability", "expected_closing_date", "assigned_to", "description")
        widgets = {
            "expected_closing_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self.fields["partner"].queryset = Partner.objects.filter(company=company) if company else Partner.objects.none()
        self.fields["assigned_to"].queryset = self.fields["assigned_to"].queryset.filter(
            is_active=True,
            company_memberships__company=company,
            company_memberships__is_active=True,
        ).order_by("username").distinct() if company else self.fields["assigned_to"].queryset.none()
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_expected_revenue(self):
        value = self.cleaned_data["expected_revenue"]
        if value < 0:
            raise forms.ValidationError("Le montant doit être positif ou nul.")
        return value


class OpportunityCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Opportunity
    form_class = OpportunityForm
    template_name = "crm/opportunity_form.html"
    permission_required = "crm.add_opportunity"
    success_url = reverse_lazy("crm:pipeline")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        from apps.core.models import ERPModule
        if not ERPModule.objects.filter(slug="crm", is_enabled=True).exists():
            raise Http404("Le module CRM est désactivé.")
        if not request.company:
            messages.error(request, "Aucune société active n’est associée à votre compte.")
            return redirect("crm:pipeline")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.company
        return kwargs

    def form_valid(self, form):
        form.instance.company = self.request.company
        if form.instance.assigned_to_id is None:
            form.instance.assigned_to = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"L’opportunité {self.object.name} a été créée.")
        return response
