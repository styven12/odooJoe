from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
class Employee(models.Model):
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='employees')
 user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='employee_profiles')
 employee_number=models.CharField(max_length=40)
 job_title=models.CharField(max_length=120,blank=True)
 hire_date=models.DateField(default=timezone.localdate)
 is_active=models.BooleanField(default=True)
 class Meta:
  ordering=['employee_number']
  constraints=[models.UniqueConstraint(fields=['company','user'],name='people_company_user_unique'),models.UniqueConstraint(fields=['company','employee_number'],name='people_company_number_unique')]
 def __str__(self):return f'{self.employee_number} · {self.user}'
class LeaveRequest(models.Model):
 class Kind(models.TextChoices): ANNUAL='ANNUAL','Congé annuel'; SICK='SICK','Maladie'; OTHER='OTHER','Autre'
 class Status(models.TextChoices): PENDING='PENDING','En attente'; APPROVED='APPROVED','Approuvé'; REJECTED='REJECTED','Refusé'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='leave_requests')
 employee=models.ForeignKey(Employee,on_delete=models.PROTECT,related_name='leave_requests')
 kind=models.CharField(max_length=10,choices=Kind.choices,default=Kind.ANNUAL)
 start_date=models.DateField()
 end_date=models.DateField()
 reason=models.TextField(blank=True)
 status=models.CharField(max_length=10,choices=Status.choices,default=Status.PENDING)
 decided_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='leave_decisions')
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:
  ordering=['-created_at']
  constraints=[models.CheckConstraint(condition=Q(end_date__gte=models.F('start_date')),name='people_leave_dates_ordered')]
 def clean(self):
  if self.employee_id and self.company_id and self.employee.company_id!=self.company_id:raise ValidationError({'employee':'L’employé doit appartenir à la société active.'})
  if self.start_date and self.end_date and self.end_date<self.start_date:raise ValidationError({'end_date':'La date de fin doit suivre la date de début.'})
class Attendance(models.Model):
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='attendance_records')
 employee=models.ForeignKey(Employee,on_delete=models.PROTECT,related_name='attendance_records')
 work_date=models.DateField(default=timezone.localdate)
 clock_in=models.TimeField(null=True,blank=True)
 clock_out=models.TimeField(null=True,blank=True)
 note=models.CharField(max_length=200,blank=True)
 class Meta:
  ordering=['-work_date']
  constraints=[models.UniqueConstraint(fields=['employee','work_date'],name='people_attendance_employee_date_unique')]
 def clean(self):
  if self.employee_id and self.company_id and self.employee.company_id!=self.company_id:raise ValidationError({'employee':'L’employé doit appartenir à la société active.'})
  if self.clock_in and self.clock_out and self.clock_out<=self.clock_in:raise ValidationError({'clock_out':'L’heure de sortie doit suivre l’heure d’arrivée.'})
class ExpenseReport(models.Model):
 class Status(models.TextChoices): PENDING='PENDING','En attente'; APPROVED='APPROVED','Approuvée'; REJECTED='REJECTED','Refusée'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='expense_reports')
 employee=models.ForeignKey(Employee,on_delete=models.PROTECT,related_name='expenses')
 expense_date=models.DateField(default=timezone.localdate)
 category=models.CharField(max_length=100)
 description=models.CharField(max_length=220)
 amount=models.DecimalField(max_digits=12,decimal_places=2)
 currency=models.CharField(max_length=3,default='XAF')
 status=models.CharField(max_length=10,choices=Status.choices,default=Status.PENDING)
 decided_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='expense_decisions')
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:
  ordering=['-expense_date','-created_at']
  constraints=[models.CheckConstraint(condition=Q(amount__gt=0),name='people_expense_amount_positive')]
 def clean(self):
  if self.employee_id and self.company_id and self.employee.company_id!=self.company_id:raise ValidationError({'employee':'L’employé doit appartenir à la société active.'})
class Payslip(models.Model):
 class Status(models.TextChoices): DRAFT='DRAFT','Brouillon'; APPROVED='APPROVED','Validé'; REJECTED='REJECTED','Refusé'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='payslips')
 employee=models.ForeignKey(Employee,on_delete=models.PROTECT,related_name='payslips')
 period_start=models.DateField()
 period_end=models.DateField()
 gross_amount=models.DecimalField(max_digits=12,decimal_places=2)
 deductions=models.DecimalField(max_digits=12,decimal_places=2,default=0)
 currency=models.CharField(max_length=3,default='XAF')
 status=models.CharField(max_length=10,choices=Status.choices,default=Status.DRAFT)
 created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name='payslips_created')
 decided_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='payslips_decided')
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:
  ordering=['-period_start','employee__employee_number']
  constraints=[models.UniqueConstraint(fields=['employee','period_start','period_end'],name='people_payslip_employee_period_unique'),models.CheckConstraint(condition=Q(period_end__gte=models.F('period_start')),name='people_payslip_period_ordered'),models.CheckConstraint(condition=Q(gross_amount__gte=0),name='people_payslip_gross_nonnegative'),models.CheckConstraint(condition=Q(deductions__gte=0),name='people_payslip_deductions_nonnegative'),models.CheckConstraint(condition=Q(deductions__lte=models.F('gross_amount')),name='people_payslip_deductions_lte_gross')]
 @property
 def net_amount(self):return self.gross_amount-self.deductions
 def clean(self):
  if self.employee_id and self.company_id and self.employee.company_id!=self.company_id:raise ValidationError({'employee':'L’employé doit appartenir à la société active.'})
  if self.period_start and self.period_end and self.period_end<self.period_start:raise ValidationError({'period_end':'La période est invalide.'})
  if self.deductions is not None and self.gross_amount is not None and self.deductions>self.gross_amount:raise ValidationError({'deductions':'Les retenues ne peuvent dépasser le brut.'})
