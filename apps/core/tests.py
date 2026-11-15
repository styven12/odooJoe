from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.companies.models import Company, CompanyMembership
from .models import ERPModule


class ModuleCatalogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="catalog-admin", password="test-password")
        company = Company.objects.create(name="Catalogue", code="CATALOG")
        CompanyMembership.objects.create(user=self.user, company=company)
        self.client.force_login(self.user)

    def test_catalog_marks_operational_modules_as_available(self):
        ERPModule.objects.create(slug="pos", name="Point de vente", is_enabled=True)

        response = self.client.get(reverse("module_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Activé")
        self.assertContains(response, reverse("retail:pos"))
        self.assertContains(response, reverse("toggle_module", args=["pos"]))

    def test_operational_module_can_be_disabled_from_catalog(self):
        module = ERPModule.objects.create(slug="pos", name="Point de vente", is_enabled=False)

        response = self.client.post(reverse("toggle_module", args=[module.slug]))

        self.assertEqual(response.status_code, 302)
        module.refresh_from_db()
        self.assertTrue(module.is_enabled)
