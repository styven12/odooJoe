from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.companies.models import Company,CompanyMembership
from apps.core.models import ERPModule
from .models import Project,ProjectTask,TimeEntry
class ProjectTimesheetTests(TestCase):
 def setUp(self):
  self.user=get_user_model().objects.create_superuser(username='project-admin',email='project@example.test',password='test-password')
  self.company=Company.objects.create(name='Projet Test',code='PROJECTTEST')
  CompanyMembership.objects.create(company=self.company,user=self.user,role=CompanyMembership.Role.OWNER)
  ERPModule.objects.create(slug='projects',name='Projets',is_enabled=True)
  ERPModule.objects.create(slug='timesheets',name='Temps',is_enabled=True)
  self.client.force_login(self.user);session=self.client.session;session['active_company_id']=self.company.pk;session.save()
 def test_project_task_time_entry_flow(self):
  self.client.post(reverse('projects:create'),{'name':'Migration ERP','description':'','start_date':'2026-11-12','due_date':'2026-12-01'})
  project=Project.objects.get(company=self.company)
  response=self.client.post(reverse('projects:create_task',args=[project.pk]),{'title':'Configurer le stock','assigned_to':self.user.pk,'due_date':'2026-11-20'})
  self.assertEqual(response.status_code,302)
  task=ProjectTask.objects.get(project=project)
  self.client.post(reverse('projects:timesheets'),{'task':task.pk,'work_date':'2026-11-12','hours':'7.5','description':'Configuration'})
  self.assertEqual(TimeEntry.objects.get(task=task).hours,Decimal('7.50'))
  self.assertContains(self.client.get(reverse('projects:timesheets')),'7,50')
 def test_cannot_add_task_to_another_company_project(self):
  foreign=Company.objects.create(name='Autre',code='OTHERPROJECT')
  project=Project.objects.create(company=foreign,name='Secret')
  response=self.client.post(reverse('projects:create_task',args=[project.pk]),{'title':'Intrusion'})
  self.assertEqual(response.status_code,404)
  self.assertFalse(ProjectTask.objects.filter(project=project).exists())


