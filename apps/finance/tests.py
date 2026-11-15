from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.companies.models import Company,CompanyMembership
from apps.core.models import ERPModule
from .models import LedgerAccount,JournalEntry,TreasuryAccount,TreasuryMovement
class FinanceTests(TestCase):
 def setUp(self):
  self.user=get_user_model().objects.create_superuser(username='finance-admin',email='finance@example.test',password='test-password');self.company=Company.objects.create(name='Finance Test',code='FINTEST');CompanyMembership.objects.create(company=self.company,user=self.user,role=CompanyMembership.Role.OWNER)
  for slug in ('accounting','treasury'):ERPModule.objects.create(slug=slug,name=slug,is_enabled=True)
  self.cash=LedgerAccount.objects.create(company=self.company,code='101',name='Caisse',kind=LedgerAccount.Kind.ASSET);self.sales=LedgerAccount.objects.create(company=self.company,code='701',name='Ventes',kind=LedgerAccount.Kind.INCOME)
  self.client.force_login(self.user);session=self.client.session;session['active_company_id']=self.company.pk;session.save()
 def test_journal_entry_posts_balanced_debit_and_credit(self):
  response=self.client.post(reverse('finance:create_entry'),{'entry_date':'2026-11-12','description':'Vente au comptant','debit_account':self.cash.pk,'credit_account':self.sales.pk,'amount':'15000'})
  self.assertEqual(response.status_code,302);entry=JournalEntry.objects.get();self.assertEqual(entry.state,JournalEntry.State.DRAFT)
  response=self.client.post(reverse('finance:post_entry',args=[entry.pk]));self.assertEqual(response.status_code,302);entry.refresh_from_db();self.assertEqual(entry.state,JournalEntry.State.POSTED)
  self.assertContains(self.client.get(reverse('finance:accounting')),'15000')
 def test_treasury_blocks_outflow_beyond_available_balance(self):
  account=TreasuryAccount.objects.create(company=self.company,name='Caisse principale',kind=TreasuryAccount.Kind.CASH,opening_balance=Decimal('1000'))
  self.client.post(reverse('finance:create_treasury_movement'),{'account':account.pk,'direction':'OUT','movement_date':'2026-11-12','amount':'1500','description':'Sortie'})
  self.assertEqual(TreasuryMovement.objects.count(),0);self.assertEqual(account.balance,Decimal('1000'))
  self.client.post(reverse('finance:create_treasury_movement'),{'account':account.pk,'direction':'OUT','movement_date':'2026-11-12','amount':'700','description':'Sortie'})
  self.assertEqual(account.balance,Decimal('300'))
