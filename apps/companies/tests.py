from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Company, CompanyMembership


class ActiveCompanyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="company-user", password="test-password")
        self.first = Company.objects.create(name="Société une", code="CMP001")
        self.second = Company.objects.create(name="Société deux", code="CMP002")
        CompanyMembership.objects.create(company=self.first, user=self.user)
        self.client.force_login(self.user)

    def test_user_can_switch_only_to_a_company_they_belong_to(self):
        CompanyMembership.objects.create(company=self.second, user=self.user)

        response = self.client.post(reverse("select_company"), {"company_id": self.second.pk, "next": "/crm/"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/crm/")
        dashboard = self.client.get(reverse("dashboard"))
        self.assertEqual(dashboard.context["active_company"], self.second)

    def test_external_next_url_is_rejected_and_other_companies_are_not_selectable(self):
        response = self.client.post(reverse("select_company"), {"company_id": self.second.pk, "next": "//example.invalid/"})

        self.assertRedirects(response, reverse("dashboard"))
        dashboard = self.client.get(reverse("dashboard"))
        self.assertEqual(dashboard.context["active_company"], self.first)
