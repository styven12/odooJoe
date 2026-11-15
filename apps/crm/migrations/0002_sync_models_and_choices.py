import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0001_initial"),
        ("crm", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="activity",
            options={
                "ordering": ["status", "due_at"],
                "verbose_name": "Activité commerciale",
                "verbose_name_plural": "Activités commerciales",
            },
        ),
        migrations.AlterModelOptions(
            name="lead",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Prospect",
                "verbose_name_plural": "Prospects",
            },
        ),
        migrations.AlterModelOptions(
            name="opportunity",
            options={
                "ordering": ["-updated_at"],
                "verbose_name": "Opportunité",
                "verbose_name_plural": "Opportunités",
            },
        ),
        migrations.AlterModelOptions(
            name="partner",
            options={
                "ordering": ["name"],
                "verbose_name": "Partenaire",
                "verbose_name_plural": "Partenaires",
            },
        ),
        migrations.RemoveConstraint(
            model_name="opportunity",
            name="crm_probability_0_100",
        ),
        migrations.RenameField(
            model_name="activity",
            old_name="kind",
            new_name="activity_type",
        ),
        migrations.RenameField(
            model_name="partner",
            old_name="kind",
            new_name="partner_type",
        ),
        migrations.AddField(
            model_name="activity",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="lead",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="opportunity",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="partner",
            name="address",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="partner",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="partner",
            name="website",
            field=models.URLField(blank=True),
        ),
        migrations.AlterField(
            model_name="activity",
            name="activity_type",
            field=models.CharField(
                choices=[
                    ("CALL", "Appel"),
                    ("MEETING", "Réunion"),
                    ("EMAIL", "E-mail"),
                    ("TASK", "Tâche"),
                    ("FOLLOWUP", "Relance"),
                ],
                default="TASK",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_crm_activities",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="due_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name="activity",
            name="lead",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="activities",
                to="crm.lead",
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="opportunity",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="activities",
                to="crm.opportunity",
            ),
        ),
        migrations.AlterField(
            model_name="activity",
            name="partner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="activities",
                to="crm.partner",
            ),
        ),
        migrations.AlterField(
            model_name="lead",
            name="assigned_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_crm_leads",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="lead",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_crm_leads",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="lead",
            name="title",
            field=models.CharField(max_length=180, verbose_name="Sujet du prospect"),
        ),
        migrations.AlterField(
            model_name="opportunity",
            name="name",
            field=models.CharField(
                max_length=180,
                verbose_name="Nom de l'opportunité",
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_crm_partners",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="name",
            field=models.CharField(
                max_length=180,
                verbose_name="Nom / Raison sociale",
            ),
        ),
        migrations.AlterField(
            model_name="partner",
            name="partner_type",
            field=models.CharField(
                choices=[
                    ("LEAD", "Prospect"),
                    ("CUSTOMER", "Client"),
                    ("BOTH", "Prospect et client"),
                    ("SUPPLIER", "Fournisseur"),
                ],
                default="LEAD",
                max_length=20,
                verbose_name="Type de partenaire",
            ),
        ),
        migrations.AddConstraint(
            model_name="opportunity",
            constraint=models.CheckConstraint(
                condition=models.Q(("probability__gte", 0), ("probability__lte", 100)),
                name="crm_probability_between_0_100",
            ),
        ),
        migrations.AddConstraint(
            model_name="opportunity",
            constraint=models.CheckConstraint(
                condition=models.Q(("expected_revenue__gte", 0)),
                name="crm_revenue_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="partner",
            constraint=models.UniqueConstraint(
                condition=models.Q(("email", ""), _negated=True),
                fields=("company", "email"),
                name="crm_unique_partner_email",
            ),
        ),
    ]
