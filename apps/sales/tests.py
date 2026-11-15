from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.companies.models import Company, CompanyMembership
from apps.core.models import ERPModule
from apps.crm.models import Opportunity, Partner
from .models import Invoice, SalesOrder


class SalesFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="sales-user", password="test-password")
        self.company = Company.objects.create(name="Société ventes", code="SALESTEST")
        CompanyMembership.objects.create(company=self.company, user=self.user, role=CompanyMembership.Role.MANAGER)
        ERPModule.objects.create(slug="sales", name="Ventes", is_enabled=True)
        ERPModule.objects.create(slug="invoicing", name="Facturation", is_enabled=True)
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="crm",
            codename__in=("view_partner", "view_lead", "view_opportunity", "view_activity"),
        ))
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="sales",
            codename__in=("view_salesorder", "add_salesorder", "confirm_salesorder", "view_invoice", "change_invoice"),
        ))
        self.partner = Partner.objects.create(company=self.company, name="Client test")
        self.opportunity = Opportunity.objects.create(
            company=self.company,
            partner=self.partner,
            name="Contrat test",
            expected_revenue=Decimal("125000.00"),
        )
        self.client.force_login(self.user)

    def test_opportunity_quote_confirmation_invoice_and_payment(self):
        response = self.client.post(reverse("sales:create_quote", args=[self.opportunity.pk]))
        self.assertRedirects(response, reverse("sales:orders"))
        order = SalesOrder.objects.get(opportunity=self.opportunity)
        self.assertEqual(order.state, SalesOrder.State.QUOTATION)
        self.assertTrue(order.number.startswith("QUO-"))
        export = self.client.get(reverse("sales:export_orders"))
        self.assertEqual(export.status_code, 200)
        self.assertContains(export, order.number)

        response = self.client.post(reverse("sales:confirm_order", args=[order.pk]))
        self.assertRedirects(response, reverse("sales:invoices"))
        order.refresh_from_db()
        invoice = Invoice.objects.get(sales_order=order)
        self.assertEqual(order.state, SalesOrder.State.CONFIRMED)
        self.assertEqual(invoice.amount, Decimal("125000.00"))
        self.assertEqual(invoice.status, Invoice.Status.OPEN)
        self.assertContains(self.client.get(reverse("sales:export_invoices")), invoice.number)

        self.client.post(reverse("sales:pay_invoice", args=[invoice.pk]))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertIsNotNone(invoice.paid_at)

    def test_user_cannot_confirm_another_company_order(self):
        other_company = Company.objects.create(name="Autre société", code="OTHER")
        other_partner = Partner.objects.create(company=other_company, name="Autre client")
        other_opportunity = Opportunity.objects.create(company=other_company, partner=other_partner, name="Privée")
        order = SalesOrder.objects.create(
            company=other_company,
            customer=other_partner,
            opportunity=other_opportunity,
            amount=Decimal("1.00"),
        )

        response = self.client.post(reverse("sales:confirm_order", args=[order.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Invoice.objects.filter(sales_order=order).exists())
        list_response = self.client.get(reverse("sales:orders"))
        self.assertNotContains(list_response, "Autre client")
