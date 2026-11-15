from django.core.management.base import BaseCommand
from apps.core.models import ERPModule

MODULES = [
    ("crm", "CRM", "Prospects, opportunités et activités commerciales."),
    ("sales", "Ventes", "Devis, commandes clients et conditions commerciales."),
    ("inventory", "Stocks", "Articles, niveaux de stock et mouvements d’entrée ou de sortie."),
    ("purchasing", "Achats", "Commandes fournisseurs et réception des articles en stock."),
    ("projects", "Projets", "Projets, tâches, responsables et échéances."),
    ("timesheets", "Feuilles de temps", "Saisie des heures par projet et tâche."),
    ("employees", "Employés", "Dossiers des collaborateurs de la société."),
    ("leaves", "Congés et absences", "Demandes de congé avec circuit de validation."),
    ("attendance", "Temps et pointages", "Enregistrement des heures de présence."),
    ("expenses", "Notes de frais", "Soumission et validation des frais professionnels."),
    ("assets", "Actifs et flotte", "Registre des équipements et de leur état."),
    ("maintenance", "Maintenance", "Planification et suivi des interventions."),
    ("helpdesk", "Support client", "Tickets clients avec suivi de résolution."),
    ("manufacturing", "Fabrication", "Nomenclatures, composants et ordres de fabrication."),
    ("shipping", "Expéditions", "Préparation, expédition et confirmation des livraisons."),
    ("documents", "Gestion documentaire", "Bibliothèque sécurisée de fichiers par société."),
    ("payroll", "Pré-paie", "Préparation manuelle et validation des bulletins."),
    ("accounting", "Comptabilité", "Plan comptable simple et journal d’écritures équilibrées."),
    ("treasury", "Trésorerie", "Comptes de caisse ou banque et mouvements suivis."),
    ("pos", "Point de vente", "Sessions de caisse, tickets et suivi des espèces."),
    ("ecommerce", "E-commerce", "Catalogue en ligne et commandes à confirmer."),
    ("invoicing", "Facturation", "Factures clients et fournisseurs."),
]

IMPLEMENTED_MODULES = {"crm", "sales", "invoicing", "inventory", "purchasing", "projects", "timesheets", "employees", "leaves", "attendance", "expenses", "assets", "maintenance", "helpdesk", "manufacturing", "shipping", "documents", "payroll", "accounting", "treasury", "pos", "ecommerce"}

class Command(BaseCommand):
    help = "Crée ou met à jour le catalogue des 22 modules métiers du Mini-Odoo."

    def handle(self, *args, **options):
        for slug, name, description in MODULES:
            ERPModule.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "is_core": False,
                    "is_enabled": slug in IMPLEMENTED_MODULES,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"{len(MODULES)} modules métiers enregistrés."))
