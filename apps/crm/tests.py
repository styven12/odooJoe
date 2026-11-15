from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.companies.models import Company, CompanyMembership
from apps.core.models import ERPModule
from .models import Activity, Opportunity, Partner


class CrmDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="crm-user",
            email="crm-user@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.company = Company.objects.create(name="Société test", code="CRMTEST")
        ERPModule.objects.create(slug="crm", name="CRM", is_enabled=True)
        CompanyMembership.objects.create(company=self.company, user=self.user, role=CompanyMembership.Role.OWNER)
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="crm",
            codename__in=("view_partner", "view_lead", "view_opportunity", "view_activity", "add_opportunity"),
        ))
        self.partner = Partner.objects.create(
            company=self.company,
            name="Client test",
        )

    def test_dashboard_shows_activity_type_and_weighted_open_forecast(self):
        Opportunity.objects.create(
            company=self.company,
            partner=self.partner,
            name="Opportunité ouverte",
            stage=Opportunity.Stage.NEW,
            expected_revenue=Decimal("1000.00"),
            probability=50,
        )
        Opportunity.objects.create(
            company=self.company,
            partner=self.partner,
            name="Opportunité gagnée",
            stage=Opportunity.Stage.WON,
            expected_revenue=Decimal("2000.00"),
            probability=100,
        )
        Activity.objects.create(
            company=self.company,
            title="Envoyer un e-mail",
            activity_type=Activity.ActivityType.EMAIL,
        )

        response = self.client.get(reverse("crm:index"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["indicators"]["chiffre_affaires_previsionnel"],
            Decimal("500.00"),
        )
        self.assertContains(response, "E-mail")
        self.assertContains(response, "Nouveau")
        self.assertContains(response, "Chiffre d’affaires prévisionnel pondéré")

    def test_pipeline_page_renders(self):
        response = self.client.get(reverse("crm:pipeline"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pipeline commercial")
        self.assertContains(response, "Aucune opportunité")

    def test_dashboard_only_shows_records_from_active_company(self):
        other_company = Company.objects.create(name="Société privée", code="OTHER")
        other_partner = Partner.objects.create(company=other_company, name="Client privé")
        Opportunity.objects.create(company=other_company, partner=other_partner, name="Donnée privée")

        response = self.client.get(reverse("crm:index"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Donnée privée")

    def test_user_can_create_company_scoped_opportunity(self):
        response = self.client.post(reverse("crm:opportunity_create"), {
            "name": "Nouvelle opportunité",
            "partner": self.partner.pk,
            "stage": Opportunity.Stage.NEW,
            "expected_revenue": "2500.00",
            "probability": "30",
            "expected_closing_date": "",
            "assigned_to": "",
            "description": "Test de création",
        })

        self.assertEqual(response.status_code, 302)
        opportunity = Opportunity.objects.get(name="Nouvelle opportunité")
        self.assertEqual(opportunity.company, self.company)
        self.assertEqual(opportunity.assigned_to, self.user)
