"""
Tests d'intégration du Mini-Odoo.

Objectif : chaque fonctionnalité doit renvoyer un résultat utilisable, même
sur une base de données vide (aucun crash, aucun 404 injustifié).

Deux scénarios couverts :
1. ``BootStandardScenarioTests`` : base initialisée par l'auto-setup Render
   (modules, groupes, admin, société par défaut) puis parcours complet des
   modules métier (stocks, achats, projets, RH, CRM, ventes, production,
   service, documents, comptabilité, trésorerie, point de vente, e-commerce).
2. ``NoCompanyScenarioTests`` : base fraîche SANS société : toutes les pages
   doivent s'afficher (état vide) et les formulaires doivent rediriger avec un
   message explicite au lieu de planter.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.companies.models import Company, CompanyMembership
from apps.crm.models import Partner
from apps.inventory.models import Product
from apps.projects.models import ProjectTask

User = get_user_model()

ADMIN_PASSWORD = "MiniOdoo-4jjcLZJYCi"


def all_pages():
    """Toutes les pages GET du back-office (hors admin Django détaillé)."""
    return [
        reverse("dashboard"),
        reverse("module_list"),
        reverse("crm:index"),
        reverse("crm:pipeline"),
        reverse("sales:orders"),
        reverse("sales:invoices"),
        reverse("sales:export_orders"),
        reverse("sales:export_invoices"),
        reverse("inventory:stock"),
        reverse("purchasing:orders"),
        reverse("purchasing:create_order"),
        reverse("projects:list"),
        reverse("projects:timesheets"),
        reverse("people:employees"),
        reverse("people:leaves"),
        reverse("people:attendance"),
        reverse("people:expenses"),
        reverse("people:payroll"),
        reverse("service:assets"),
        reverse("service:maintenance"),
        reverse("service:tickets"),
        reverse("production:manufacturing"),
        reverse("production:shipments"),
        reverse("documents:library"),
        reverse("finance:accounting"),
        reverse("finance:treasury"),
        reverse("retail:pos"),
        reverse("retail:webshop"),
        "/accounts/password_change/",
        "/admin/",
    ]


class BootMixin:
    """Reproduit exactement les commandes exécutées par l'auto-setup Render."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_modules", verbosity=0)
        call_command("setup_roles", verbosity=0)
        call_command("ensure_admin", verbosity=0)
        call_command("seed_company", verbosity=0)
        cls.user = User.objects.get(username="admin")
        cls.company = Company.objects.get(code="MAIN")

    def login(self):
        client = self.client
        client.force_login(self.user)
        return client


class SeedCompanyTests(BootMixin, TestCase):
    def test_seed_company_idempotent(self):
        """Exécuter seed_company deux fois ne duplique rien et ne plante pas."""
        call_command("seed_company", verbosity=0)
        self.assertEqual(Company.objects.filter(code="MAIN").count(), 1)
        self.assertTrue(
            CompanyMembership.objects.filter(company=self.company, user=self.user).exists()
        )


class StandardPagesTests(BootMixin, TestCase):
    def test_all_pages_return_200(self):
        """Chaque page du back-office renvoie 200 avec l'admin connecté."""
        client = self.login()
        for page in all_pages():
            with self.subTest(page=page):
                response = client.get(page)
                self.assertEqual(
                    response.status_code, 200, f"{page} ne renvoie pas 200"
                )

    def test_real_login_flow(self):
        """Le formulaire de connexion fonctionne (POST réel)."""
        client = self.client
        client.logout()
        response = client.post(
            "/accounts/login/",
            {"username": "admin", "password": ADMIN_PASSWORD},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)

    def test_login_redirects_anonymous(self):
        """Sans session, la racine redirige vers la page de connexion."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])


class ModuleToggleTests(BootMixin, TestCase):
    def test_toggle_module_on_off(self):
        client = self.login()
        response = client.post(reverse("toggle_module", args=["crm"]))
        self.assertEqual(response.status_code, 302)
        response = client.get(reverse("crm:index"))
        # Module désactivé -> page 404 explicite (comportement voulu du catalogue)
        self.assertEqual(response.status_code, 404)
        client.post(reverse("toggle_module", args=["crm"]))
        self.assertEqual(client.get(reverse("crm:index")).status_code, 200)

    def test_select_company(self):
        client = self.login()
        response = client.post(
            reverse("select_company"),
            {"company_id": self.company.pk, "next": "/"},
        )
        self.assertEqual(response.status_code, 302)
        session = client.session
        self.assertIn("active_company_id", session)


class InventoryFlowTests(BootMixin, TestCase):
    def test_create_product_and_movement(self):
        client = self.login()
        response = client.post(
            reverse("inventory:create_product"),
            {"sku": "SKU-001", "name": "Article A", "unit": "unité", "reorder_level": "2"},
        )
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(sku="SKU-001")
        self.assertEqual(product.company, self.company)

        response = client.post(
            reverse("inventory:move_stock"),
            {"product": product.pk, "kind": "IN", "quantity": "10", "reference": "init"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(product.on_hand, Decimal("10"))

        response = client.post(
            reverse("inventory:move_stock"),
            {"product": product.pk, "kind": "OUT", "quantity": "99", "reference": "too-much"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(product.on_hand, Decimal("10"))  # sortie refusée


class ProjectsFlowTests(BootMixin, TestCase):
    def test_project_task_timesheet(self):
        client = self.login()
        response = client.post(
            reverse("projects:create"),
            {
                "name": "Projet Alpha",
                "description": "Test",
                "start_date": "2026-01-01",
                "due_date": "2026-03-01",
            },
        )
        self.assertEqual(response.status_code, 302)
        project = self.client.get(reverse("projects:list")).context["projects"][0]

        response = client.post(
            reverse("projects:create_task", args=[project.pk]),
            {"title": "Tâche 1", "assigned_to": "", "due_date": ""},
        )
        self.assertEqual(response.status_code, 302)
        # Re-lecture fraîche : le projet provient d'un queryset avec
        # prefetch_related('tasks'), dont le cache est vide.
        task = ProjectTask.objects.filter(project=project).first()
        self.assertIsNotNone(task)

        response = client.post(reverse("projects:task_status", args=[task.pk, "DONE"]))
        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.status, "DONE")

        response = client.post(
            reverse("projects:timesheets"),
            {"task": task.pk, "work_date": "2026-01-05", "hours": "3.5", "description": ""},
        )
        self.assertEqual(response.status_code, 302)


class PurchasingFlowTests(BootMixin, TestCase):
    def test_order_receive_updates_stock(self):
        client = self.login()
        supplier = Partner.objects.create(
            name="Fournisseur X", company=self.company, partner_type=Partner.PartnerType.SUPPLIER
        )
        product = Product.objects.create(sku="SKU-P", name="Article P", company=self.company)
        response = client.post(
            reverse("purchasing:create_order"),
            {
                "supplier": supplier.pk,
                "product": product.pk,
                "quantity": "5",
                "unit_cost": "100",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        order = self.client.get(reverse("purchasing:orders")).context["orders"][0]

        self.assertEqual(client.post(reverse("purchasing:action", args=[order.pk, "order"])).status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, "ORDERED")

        self.assertEqual(client.post(reverse("purchasing:action", args=[order.pk, "receive"])).status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, "RECEIVED")
        self.assertEqual(product.on_hand, Decimal("5"))


class FinanceFlowTests(BootMixin, TestCase):
    def test_accounting_and_treasury(self):
        client = self.login()
        client.post(
            reverse("finance:create_account"),
            {"code": "701", "name": "Ventes", "kind": "INCOME"},
        )
        client.post(
            reverse("finance:create_account"),
            {"code": "571", "name": "Caisse", "kind": "ASSET"},
        )
        accounts = client.get(reverse("finance:accounting")).context["accounts"]
        self.assertEqual(accounts.count(), 2)

        response = client.post(
            reverse("finance:create_entry"),
            {
                "entry_date": "2026-01-10",
                "description": "Vente comptant",
                "debit_account": accounts.get(code="571").pk,
                "credit_account": accounts.get(code="701").pk,
                "amount": "500",
            },
        )
        self.assertEqual(response.status_code, 302)
        entry = client.get(reverse("finance:accounting")).context["entries"][0]
        self.assertEqual(entry.state, "DRAFT")

        response = client.post(reverse("finance:post_entry", args=[entry.pk]))
        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.state, "POSTED")

        client.post(
            reverse("finance:create_treasury_account"),
            {"name": "Caisse principale", "kind": "CASH", "currency": "XAF", "opening_balance": "0"},
        )
        treasury_account = client.get(reverse("finance:treasury")).context["accounts"][0]
        response = client.post(
            reverse("finance:create_treasury_movement"),
            {
                "account": treasury_account.pk,
                "direction": "IN",
                "movement_date": "2026-01-10",
                "amount": "500",
                "description": "Encaissement",
                "reference": "",
            },
        )
        self.assertEqual(response.status_code, 302)


class PeopleFlowTests(BootMixin, TestCase):
    def test_employee_leave_attendance_expense_payroll(self):
        client = self.login()
        # Un second superutilisateur valide les demandes : l'auto-approbation
        # est volontairement interdite par l'application.
        approver = User.objects.create_superuser(
            username="boss", email="boss@mini-odoo.local", password="Boss-12345678"
        )
        response = client.post(
            reverse("people:employees"),
            {
                "user": self.user.pk,
                "employee_number": "EMP-001",
                "job_title": "Directeur",
                "hire_date": "2026-01-01",
            },
        )
        self.assertEqual(response.status_code, 302)

        response = client.post(
            reverse("people:leaves"),
            {"kind": "ANNUAL", "start_date": "2026-02-01", "end_date": "2026-02-05", "reason": "Repos"},
        )
        self.assertEqual(response.status_code, 302)
        leave = client.get(reverse("people:leaves")).context["leaves"][0]
        self.client.force_login(approver)
        response = self.client.post(reverse("people:leave_decision", args=[leave.pk, "APPROVED"]))
        self.assertEqual(response.status_code, 302)
        leave.refresh_from_db()
        self.assertEqual(leave.status, "APPROVED")

        # Les actions suivantes s'effectuent depuis le compte de l'employé.
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("people:attendance"),
            {"work_date": "2026-01-06", "clock_in": "08:00", "clock_out": "17:00", "note": ""},
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            reverse("people:expenses"),
            {
                "expense_date": "2026-01-07",
                "category": "Transport",
                "description": "Course client",
                "amount": "25",
            },
        )
        self.assertEqual(response.status_code, 302)
        expense = self.client.get(reverse("people:expenses")).context["expenses"][0]
        # Validation par un autre compte (auto-approbation interdite).
        self.client.force_login(approver)
        response = self.client.post(reverse("people:expense_decision", args=[expense.pk, "APPROVED"]))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("people:payroll"),
            {
                "employee": self.user.employee_profiles.get(company=self.company).pk,
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
                "gross_amount": "500000",
                "deductions": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        slip = self.client.get(reverse("people:payroll")).context["payslips"][0]
        self.client.force_login(approver)
        response = self.client.post(reverse("people:payslip_decision", args=[slip.pk, "APPROVED"]))
        self.assertEqual(response.status_code, 302)


class CrmSalesFlowTests(BootMixin, TestCase):
    def test_opportunity_quote_confirm_pay(self):
        client = self.login()
        partner = Partner.objects.create(
            name="Client Y", company=self.company, partner_type=Partner.PartnerType.CUSTOMER
        )
        response = client.post(
            reverse("crm:opportunity_create"),
            {
                "name": "Gros contrat",
                "partner": partner.pk,
                "stage": "NEW",
                "expected_revenue": "1000000",
                "probability": "50",
                "expected_closing_date": "2026-06-30",
                "assigned_to": "",
                "description": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        opportunity = client.get(reverse("crm:pipeline")).context["pipeline_columns"][0]["opportunities"].first()
        self.assertIsNotNone(opportunity)

        response = client.post(reverse("sales:create_quote", args=[opportunity.pk]))
        self.assertEqual(response.status_code, 302)
        order = client.get(reverse("sales:orders")).context["orders"][0]

        response = client.post(reverse("sales:confirm_order", args=[order.pk]))
        self.assertEqual(response.status_code, 302)
        invoice = client.get(reverse("sales:invoices")).context["invoices"][0]
        self.assertEqual(invoice.status, "OPEN")

        response = client.post(reverse("sales:pay_invoice", args=[invoice.pk]))
        self.assertEqual(response.status_code, 302)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "PAID")

        # exports CSV
        self.assertEqual(client.get(reverse("sales:export_orders")).status_code, 200)
        self.assertEqual(client.get(reverse("sales:export_invoices")).status_code, 200)
        self.assertEqual(client.get(reverse("crm:export_opportunities")).status_code, 200)


class ProductionFlowTests(BootMixin, TestCase):
    def test_bom_manufacturing_order(self):
        client = self.login()
        finished = Product.objects.create(sku="SKU-F", name="Table", company=self.company)
        component = Product.objects.create(sku="SKU-C", name="Plateau", company=self.company)
        Product.objects.create(sku="SKU-CC", name="Vis", company=self.company)

        client.post(
            reverse("inventory:move_stock"),
            {"product": component.pk, "kind": "IN", "quantity": "10", "reference": ""},
        )
        response = client.post(
            reverse("production:create_bom"),
            {"product": finished.pk, "component": component.pk, "quantity": "2"},
        )
        self.assertEqual(response.status_code, 302)

        response = client.post(
            reverse("production:create_mo"),
            {"product": finished.pk, "quantity": "2"},
        )
        self.assertEqual(response.status_code, 302)
        order = client.get(reverse("production:manufacturing")).context["orders"][0]

        response = client.post(reverse("production:mo_action", args=[order.pk, "start"]))
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.state, "IN_PROGRESS")

        response = client.post(reverse("production:mo_action", args=[order.pk, "complete"]))
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.state, "DONE")
        finished.refresh_from_db()
        component.refresh_from_db()
        self.assertEqual(finished.on_hand, Decimal("2"))
        self.assertEqual(component.on_hand, Decimal("6"))


class ServiceFlowTests(BootMixin, TestCase):
    def test_asset_maintenance_ticket(self):
        client = self.login()
        response = client.post(
            reverse("service:assets"),
            {
                "reference": "AS-001",
                "name": "Camion 1",
                "category": "Flotte",
                "serial_number": "SN-001",
                "location": "Douala",
                "purchased_on": "2025-01-01",
            },
        )
        self.assertEqual(response.status_code, 302)
        asset = client.get(reverse("service:assets")).context["assets"][0]

        response = client.post(
            reverse("service:maintenance"),
            {
                "asset": asset.pk,
                "title": "Vidange",
                "description": "",
                "priority": "NORMAL",
                "scheduled_for": "2026-01-15",
                "assigned_to": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        job = client.get(reverse("service:maintenance")).context["jobs"][0]
        self.assertEqual(client.post(reverse("service:maintenance_status", args=[job.pk, "IN_PROGRESS"])).status_code, 302)
        self.assertEqual(client.post(reverse("service:maintenance_status", args=[job.pk, "DONE"])).status_code, 302)
        asset.refresh_from_db()
        self.assertEqual(asset.state, "ACTIVE")

        partner = Partner.objects.create(
            name="Client S", company=self.company, partner_type=Partner.PartnerType.CUSTOMER
        )
        response = client.post(
            reverse("service:tickets"),
            {
                "title": "Panne imprimante",
                "description": "L'imprimante ne répond plus",
                "partner": partner.pk,
                "priority": "HIGH",
                "assigned_to": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        ticket = client.get(reverse("service:tickets")).context["tickets"][0]
        self.assertEqual(client.post(reverse("service:ticket_status", args=[ticket.pk, "OPEN"])).status_code, 302)
        self.assertEqual(client.post(reverse("service:ticket_status", args=[ticket.pk, "RESOLVED"])).status_code, 302)
        self.assertEqual(client.post(reverse("service:ticket_status", args=[ticket.pk, "CLOSED"])).status_code, 302)


class RetailFlowTests(BootMixin, TestCase):
    def test_pos_sale_and_web_order(self):
        client = self.login()
        product = Product.objects.create(sku="SKU-R", name="Sac", company=self.company)
        client.post(
            reverse("inventory:move_stock"),
            {"product": product.pk, "kind": "IN", "quantity": "20", "reference": ""},
        )
        response = client.post(
            reverse("retail:webshop"),
            {"action": "listing", "product": product.pk, "price": "5000", "online": "on"},
        )
        self.assertEqual(response.status_code, 302)

        # Point de vente
        response = client.post(reverse("retail:pos"), {"action": "open", "opening_cash": "10000"})
        self.assertEqual(response.status_code, 302)
        response = client.post(
            reverse("retail:pos"),
            {
                "action": "sale",
                "product": product.pk,
                "quantity": "2",
                "payment_method": "CASH",
                "payment_reference": "",
                "customer_name": "Client comptoir",
            },
        )
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.on_hand, Decimal("18"))

        response = client.post(reverse("retail:pos"), {"action": "close", "closing_cash": "20000"})
        self.assertEqual(response.status_code, 302)

        # Commande web
        customer = Partner.objects.create(
            name="Client Web", company=self.company, partner_type=Partner.PartnerType.CUSTOMER
        )
        response = client.post(
            reverse("retail:webshop"),
            {"action": "order", "listing": "1", "customer": customer.pk, "quantity": "1"},
        )
        self.assertEqual(response.status_code, 302)
        order = client.get(reverse("retail:webshop")).context["orders"][0]
        response = client.post(reverse("retail:confirm_web_order", args=[order.pk]))
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.state, "CONFIRMED")


@override_settings(MEDIA_ROOT="/tmp/test_media_miniodoo")
class DocumentsFlowTests(BootMixin, TestCase):
    def test_upload_and_download(self):
        client = self.login()
        upload = SimpleUploadedFile("note.txt", b"Contenu du document de test", content_type="text/plain")
        response = client.post(
            reverse("documents:library"),
            {"title": "Note interne", "category": "RH", "file": upload},
        )
        self.assertEqual(response.status_code, 302)
        document = client.get(reverse("documents:library")).context["documents"][0]

        response = client.get(reverse("documents:download", args=[document.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"Contenu du document de test")


class NoCompanyScenarioTests(TestCase):
    """
    Base fraîche SANS société (le scénario qui provoquait les 404 / 500) :
    toutes les pages s'affichent avec un état vide et les POST redirigent
    proprement avec un message explicite.
    """

    @classmethod
    def setUpTestData(cls):
        call_command("seed_modules", verbosity=0)
        call_command("setup_roles", verbosity=0)
        call_command("ensure_admin", verbosity=0)
        cls.user = User.objects.get(username="admin")

    def login(self):
        client = self.client
        client.force_login(self.user)
        return client

    def test_all_pages_return_200_without_company(self):
        """Aucune page ne doit renvoyer 404 ni 500 sans société active."""
        client = self.login()
        for page in all_pages():
            with self.subTest(page=page):
                response = client.get(page)
                self.assertIn(
                    response.status_code,
                    (200,),
                    f"{page} renvoie {response.status_code} sans société active",
                )

    def test_dashboard_and_lists_are_empty_not_broken(self):
        client = self.login()
        response = client.get(reverse("inventory:stock"))
        self.assertEqual(list(response.context["rows"]), [])
        response = client.get(reverse("sales:orders"))
        self.assertEqual(list(response.context["orders"]), [])

    def test_post_forms_redirect_with_message_without_company(self):
        """Les créations sans société redirigent avec un message, sans crash."""
        client = self.login()
        posts = [
            (reverse("inventory:create_product"), {"sku": "X", "name": "X", "unit": "u", "reorder_level": "0"}),
            (reverse("projects:create"), {"name": "P", "description": "", "start_date": "2026-01-01", "due_date": ""}),
            (reverse("finance:create_account"), {"code": "999", "name": "X", "kind": "EXPENSE"}),
            (reverse("people:employees"), {"user": self.user.pk, "employee_number": "E1", "job_title": "", "hire_date": "2026-01-01"}),
            (reverse("purchasing:create_order"), {"supplier": "", "product": "", "quantity": "1", "unit_cost": "1", "notes": ""}),
            (reverse("retail:pos"), {"action": "open", "opening_cash": "0"}),
            (reverse("service:assets"), {"reference": "R", "name": "R", "category": "", "serial_number": "", "location": "", "purchased_on": "2026-01-01"}),
            (reverse("crm:opportunity_create"), {"name": "O", "partner": "", "stage": "NEW", "expected_revenue": "0", "probability": "10", "expected_closing_date": "", "assigned_to": "", "description": ""}),
            (reverse("finance:create_treasury_account"), {"name": "C", "kind": "CASH", "currency": "XAF", "opening_balance": "0"}),
        ]
        for url, data in posts:
            with self.subTest(url=url):
                response = client.post(url, data)
                self.assertEqual(
                    response.status_code, 302, f"POST {url} ne redirige pas (crash ?)"
                )

    def test_no_objects_created_without_company(self):
        client = self.login()
        client.post(
            reverse("inventory:create_product"),
            {"sku": "X", "name": "X", "unit": "u", "reorder_level": "0"},
        )
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(Company.objects.count(), 0)


# ---------------------------------------------------------------------------
# Round 3 — ressources navigateur, pages d'erreur habillées, couverture de
# routes et régressions des crashes corrigés.
# ---------------------------------------------------------------------------

from django.urls import get_resolver, NoReverseMatch  # noqa: E402
from apps.core.models import ERPModule  # noqa: E402
from apps.documents.models import DocumentRecord  # noqa: E402
from apps.finance.models import JournalEntry, LedgerAccount  # noqa: E402
from apps.retail.models import POSSession  # noqa: E402


class AssetsAndBrowserRoutesTests(BootMixin, TestCase):
    """Le navigateur demande favicon.ico et robots.txt à chaque visite :
    ces routes doivent renvoyer un résultat (jamais 404)."""

    def test_favicon_route_redirects_to_svg(self):
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/static/"))

    def test_favicon_svg_asset_present_in_static_finders(self):
        from django.contrib.staticfiles import finders

        path = finders.find("favicon.svg")
        self.assertTrue(path, "favicon.svg introuvable dans les finders staticfiles")

    def test_robots_txt_served_as_plain_text(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/plain"))
        self.assertContains(response, "User-agent")

    def test_favicon_linked_in_base_layout(self):
        client = self.login()
        response = client.get(reverse("dashboard"))
        self.assertContains(response, 'rel="icon"')


class ErrorPagesTests(BootMixin, TestCase):
    """Toute erreur HTTP renvoie une page habillée avec navigation —
    jamais une page blanche « Not Found » sans résultat."""

    def test_unknown_url_returns_branded_404(self):
        response = self.client.get("/cette/page/nexiste-pas/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page introuvable", status_code=404)
        self.assertContains(response, "Mini-Odoo", status_code=404)

    def test_disabled_module_404_shows_business_message(self):
        client = self.login()
        ERPModule.objects.filter(slug="crm").update(is_enabled=False)
        response = client.get(reverse("crm:index"))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "CRM", status_code=404)

    def test_post_only_route_returns_branded_405(self):
        client = self.login()
        response = client.get(reverse("inventory:create_product"))
        self.assertEqual(response.status_code, 405)
        self.assertContains(response, "405", status_code=405)
        self.assertContains(response, "formulaire", status_code=405)

    def test_permission_denied_is_branded_403(self):
        user = User.objects.create_user(username="sans-perms", password="test-password")
        CompanyMembership.objects.create(company=self.company, user=user)
        client = self.client
        client.force_login(user)
        response = client.get(reverse("inventory:stock"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Accès refusé", status_code=403)

    def test_csrf_failure_page_is_branded(self):
        strict_client = self.client_class(enforce_csrf_checks=True)
        response = strict_client.post(reverse("set_language"), {"language": "fr"})
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "CSRF", status_code=403)

    def test_500_handler_renders_standalone_page(self):
        from config.error_handlers import error_500

        response = error_500(None)
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"500", response.content)


class RouteCoverageTests(BootMixin, TestCase):
    """Couverture dynamique : chaque route nommée sans argument obligatoire
    répond 200/302/405 (jamais 404 ni 500), même sur base vide."""

    SKIP_NAMES = {"logout"}  # GET /accounts/logout/ -> 405 attendu (Django 5)

    def _collect_names(self, patterns, namespace=""):
        names = set()
        for pattern in patterns:
            ns = getattr(pattern, "namespace", "") or namespace
            if hasattr(pattern, "url_patterns"):
                names |= self._collect_names(pattern.url_patterns, ns)
                continue
            name = getattr(pattern, "name", None)
            if name:
                names.add(f"{ns}:{name}" if ns else name)
        return names

    def test_all_named_routes_without_args_are_usable(self):
        client = self.login()
        names = self._collect_names(get_resolver().url_patterns)
        checked = 0
        for full_name in sorted(names):
            if full_name in self.SKIP_NAMES or full_name.startswith("admin:"):
                continue
            try:
                url = reverse(full_name)
            except NoReverseMatch:
                continue  # route avec arguments obligatoires : couverte ailleurs
            with self.subTest(url=url):
                response = client.get(url)
                self.assertIn(
                    response.status_code,
                    (200, 302, 405),
                    f"{full_name} ({url}) renvoie {response.status_code}",
                )
                checked += 1
        self.assertGreaterEqual(checked, 40, "trop peu de routes vérifiées")


class HardeningRegressionsTests(BootMixin, TestCase):
    """Régressions des crashs corrigés : aucune action ne doit renvoyer 500."""

    def test_pos_close_without_open_session_redirects(self):
        client = self.login()
        response = client.post(reverse("retail:pos"), {"action": "close", "closing_cash": "1000"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(POSSession.objects.count(), 0)

    def test_pos_sale_without_open_session_redirects(self):
        client = self.login()
        product = Product.objects.create(sku="SKU-NS", name="Sans session", company=self.company)
        response = client.post(
            reverse("retail:pos"),
            {"action": "sale", "product": product.pk, "quantity": "1", "payment_method": "CASH"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(POSSession.objects.count(), 0)

    def test_pos_sale_invalid_form_with_open_session_redirects(self):
        client = self.login()
        product = Product.objects.create(sku="SKU-IV", name="Invalide", company=self.company)
        client.post(reverse("retail:pos"), {"action": "open", "opening_cash": "0"})
        response = client.post(
            reverse("retail:pos"),
            {"action": "sale", "product": "", "quantity": "1", "payment_method": "CASH"},
        )
        self.assertEqual(response.status_code, 302)
        session = POSSession.objects.get()
        self.assertEqual(session.state, POSSession.State.OPEN)

    def test_posting_invalid_journal_entry_shows_message_and_stays_draft(self):
        client = self.login()
        account = LedgerAccount.objects.create(
            company=self.company, code="401", name="Fournisseurs", kind="LIABILITY"
        )
        # Écriture invalide créée volontairement hors du circuit de validation.
        entry = JournalEntry.objects.create(
            company=self.company,
            entry_date="2026-01-05",
            description="Auto-équilibrage invalide",
            debit_account=account,
            credit_account=account,
            amount=Decimal("100"),
        )
        response = client.post(reverse("finance:post_entry", args=[entry.pk]))
        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.state, JournalEntry.State.DRAFT)

    @override_settings(MEDIA_ROOT="/tmp/test_media_miniodoo_missing")
    def test_document_download_with_missing_file_redirects_with_message(self):
        client = self.login()
        document = DocumentRecord.objects.create(
            company=self.company,
            title="Document disparu",
            category="RH",
            file="",
            original_name="gone.txt",
            size_bytes=0,
            uploaded_by=self.user,
        )
        response = client.get(reverse("documents:download", args=[document.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("documents:library"))
