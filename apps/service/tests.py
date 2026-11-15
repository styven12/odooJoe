from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.companies.models import Company,CompanyMembership
from apps.core.models import ERPModule
from .models import Asset,MaintenanceRequest,HelpdeskTicket
class ServiceWorkflowTests(TestCase):
 def setUp(self):
  self.user=get_user_model().objects.create_superuser(username='service-admin',email='service@example.test',password='test-password');self.company=Company.objects.create(name='Service Test',code='SERVICETEST');CompanyMembership.objects.create(company=self.company,user=self.user,role=CompanyMembership.Role.OWNER)
  for slug in ('assets','maintenance','helpdesk'):ERPModule.objects.create(slug=slug,name=slug,is_enabled=True)
  self.asset=Asset.objects.create(company=self.company,reference='EQ-1',name='Serveur')
  self.client.force_login(self.user);session=self.client.session;session['active_company_id']=self.company.pk;session.save()
 def test_maintenance_changes_asset_state_and_closes(self):
  response=self.client.post(reverse('service:maintenance'),{'asset':self.asset.pk,'title':'Ventilation','description':'','priority':'HIGH','scheduled_for':'2026-11-20','assigned_to':''})
  self.assertEqual(response.status_code,302);job=MaintenanceRequest.objects.get()
  self.client.post(reverse('service:maintenance_status',args=[job.pk,'IN_PROGRESS']));self.asset.refresh_from_db();self.assertEqual(self.asset.state,Asset.State.REPAIR)
  self.client.post(reverse('service:maintenance_status',args=[job.pk,'DONE']));self.asset.refresh_from_db();job.refresh_from_db();self.assertEqual(self.asset.state,Asset.State.ACTIVE);self.assertEqual(job.state,MaintenanceRequest.State.DONE)
 def test_helpdesk_ticket_transitions_follow_workflow(self):
  self.client.post(reverse('service:tickets'),{'title':'Connexion','description':'Client cannot connect','priority':'URGENT','partner':'','assigned_to':''})
  ticket=HelpdeskTicket.objects.get();self.assertTrue(ticket.number.startswith('TKT-'))
  self.client.post(reverse('service:ticket_status',args=[ticket.pk,'RESOLVED']));ticket.refresh_from_db();self.assertEqual(ticket.state,HelpdeskTicket.State.RESOLVED)
  self.client.post(reverse('service:ticket_status',args=[ticket.pk,'CLOSED']));ticket.refresh_from_db();self.assertEqual(ticket.state,HelpdeskTicket.State.CLOSED)
 def test_other_company_asset_cannot_be_maintained(self):
  other=Company.objects.create(name='Other',code='OTHERSERVICE');foreign=Asset.objects.create(company=other,reference='SECRET',name='Private')
  response=self.client.post(reverse('service:maintenance'),{'asset':foreign.pk,'title':'Intrusion'})
  self.assertEqual(response.status_code,200);self.assertFalse(MaintenanceRequest.objects.filter(asset=foreign).exists())
