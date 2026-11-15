from datetime import date,time
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from apps.companies.models import Company,CompanyMembership
from apps.core.models import ERPModule
from .models import Employee,LeaveRequest,Attendance,ExpenseReport,Payslip
class PeopleWorkflowTests(TestCase):
 def setUp(self):
  User=get_user_model();self.admin=User.objects.create_superuser(username='hr-admin',email='hr@test.invalid',password='test-password');self.company=Company.objects.create(name='RH test',code='HRTEST');CompanyMembership.objects.create(company=self.company,user=self.admin,role=CompanyMembership.Role.OWNER);self.employee=Employee.objects.create(company=self.company,user=self.admin,employee_number='HR-001');
  for slug in ('employees','leaves','attendance','expenses','payroll'):ERPModule.objects.create(slug=slug,name=slug,is_enabled=True)
  self.client.force_login(self.admin);session=self.client.session;session['active_company_id']=self.company.pk;session.save()
 def test_leave_request_and_conflicting_date_rejected(self):
  payload={'kind':'ANNUAL','start_date':'2026-12-01','end_date':'2026-12-03','reason':'Repos'}
  self.client.post(reverse('people:leaves'),payload);self.assertEqual(LeaveRequest.objects.count(),1)
  self.client.post(reverse('people:leaves'),payload);self.assertEqual(LeaveRequest.objects.count(),1)
 def test_attendance_can_be_completed_later_same_day(self):
  self.client.post(reverse('people:attendance'),{'work_date':'2026-11-12','clock_in':'08:00','clock_out':'','note':''})
  self.client.post(reverse('people:attendance'),{'work_date':'2026-11-12','clock_in':'08:00','clock_out':'17:00','note':''})
  self.assertEqual(Attendance.objects.count(),1);self.assertEqual(Attendance.objects.get().clock_out,time(17,0))
 def test_expense_submission_and_other_user_approval(self):
  self.client.post(reverse('people:expenses'),{'expense_date':'2026-11-12','category':'Transport','description':'Taxi client','amount':'3500'})
  expense=ExpenseReport.objects.get();self.assertEqual(expense.status,ExpenseReport.Status.PENDING)
  manager=get_user_model().objects.create_user(username='approver',password='test-password');CompanyMembership.objects.create(company=self.company,user=manager,role=CompanyMembership.Role.MANAGER);manager.user_permissions.add(*Permission.objects.filter(content_type__app_label='people'))
  self.client.force_login(manager);session=self.client.session;session['active_company_id']=self.company.pk;session.save()
  response=self.client.post(reverse('people:expense_decision',args=[expense.pk,'APPROVED']))
  self.assertEqual(response.status_code,302);expense.refresh_from_db();self.assertEqual(expense.status,ExpenseReport.Status.APPROVED)
 def test_manual_pre_pay_calculates_net_and_requires_other_approver(self):
  response=self.client.post(reverse('people:payroll'),{'employee':self.employee.pk,'period_start':'2026-10-01','period_end':'2026-10-31','gross_amount':'500000','deductions':'25000'})
  self.assertEqual(response.status_code,302);slip=Payslip.objects.get();self.assertEqual(slip.net_amount,Decimal('475000'))
  self.assertEqual(self.client.post(reverse('people:payslip_decision',args=[slip.pk,'APPROVED'])).status_code,403)
  manager=get_user_model().objects.create_user(username='payroll-approver',password='test-password');CompanyMembership.objects.create(company=self.company,user=manager,role=CompanyMembership.Role.MANAGER);manager.user_permissions.add(*Permission.objects.filter(content_type__app_label='people'))
  self.client.force_login(manager);session=self.client.session;session['active_company_id']=self.company.pk;session.save()
  self.client.post(reverse('people:payslip_decision',args=[slip.pk,'APPROVED']))
  self.assertEqual(Payslip.objects.get().status,Payslip.Status.APPROVED)

