from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required,permission_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.audit.models import AuditLog
from apps.core.models import ERPModule
from apps.core.guards import require_active_company
from apps.companies.models import CompanyMembership
from .models import Employee,LeaveRequest,Attendance,ExpenseReport,Payslip

def enabled(request,slug):
 if not ERPModule.objects.filter(slug=slug,is_enabled=True).exists():raise Http404('Module désactivé')
 # Sans société active : les GET affichent des listes vides ; les POST sont
 # redirigés avec un message par @require_active_company.
def members(company):return get_user_model().objects.filter(company_memberships__company=company,company_memberships__is_active=True,is_active=True).distinct()
def scoped_employees(request):return Employee.objects.filter(company=request.company,is_active=True).select_related('user')
class EmployeeForm(forms.ModelForm):
 class Meta:
  model=Employee;fields=('user','employee_number','job_title','hire_date')
  labels={'user':'Compte utilisateur','employee_number':'Matricule','job_title':'Poste','hire_date':'Date d’embauche'}
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);self.fields['user'].queryset=members(company).exclude(employee_profiles__company=company)
class LeaveForm(forms.ModelForm):
 class Meta:
  model=LeaveRequest;fields=('kind','start_date','end_date','reason')
  labels={'kind':'Type','start_date':'Date de début','end_date':'Date de fin','reason':'Motif'}
class AttendanceForm(forms.ModelForm):
 class Meta:
  model=Attendance;fields=('work_date','clock_in','clock_out','note')
  labels={'work_date':'Date','clock_in':'Heure d’arrivée','clock_out':'Heure de départ','note':'Note'}
class ExpenseForm(forms.ModelForm):
 class Meta:
  model=ExpenseReport;fields=('expense_date','category','description','amount')
  labels={'expense_date':'Date','category':'Catégorie','description':'Description','amount':'Montant'}
@login_required
@require_active_company
@permission_required('people.view_employee',raise_exception=True)
def employee_list(request):
 enabled(request,'employees')
 if request.method=='POST' and not request.user.has_perm('people.add_employee'):raise PermissionDenied
 if request.method=='POST':
  form=EmployeeForm(request.POST,company=request.company)
  if form.is_valid():
   e=form.save(commit=False);e.company=request.company
   try:e.full_clean();e.save()
   except ValidationError as ex:messages.error(request,str(ex))
   else:messages.success(request,'Dossier employé créé.');return redirect('people:employees')
 else:form=EmployeeForm(company=request.company)
 return render(request,'people/employees.html',{'employees':scoped_employees(request),'form':form})
@login_required
@require_active_company
@permission_required('people.add_leaverequest',raise_exception=True)
def leave_list(request):
 enabled(request,'leaves');employee=scoped_employees(request).filter(user=request.user).first();leaves=LeaveRequest.objects.filter(company=request.company).select_related('employee__user')
 if not request.user.has_perm('people.change_leaverequest') and employee:leaves=leaves.filter(employee=employee)
 if request.method=='POST':
  if not employee:messages.error(request,'Votre compte ne possède pas encore de dossier employé.')
  else:
   form=LeaveForm(request.POST)
   if form.is_valid():
    leave=form.save(commit=False);leave.company=request.company;leave.employee=employee
    overlapping=LeaveRequest.objects.filter(employee=employee,start_date__lte=leave.end_date,end_date__gte=leave.start_date,status__in=[LeaveRequest.Status.PENDING,LeaveRequest.Status.APPROVED])
    if overlapping.exists():form.add_error(None,'Une demande est déjà en attente ou approuvée sur ces dates.')
    else:
     try:leave.full_clean();leave.save()
     except ValidationError as ex:form.add_error(None,ex)
     else:messages.success(request,'Demande de congé envoyée.');return redirect('people:leaves')
   return render(request,'people/leaves.html',{'leaves':leaves,'form':form})
  return redirect('people:leaves')
 form=LeaveForm();return render(request,'people/leaves.html',{'leaves':leaves,'form':form})
@login_required
@require_POST
@require_active_company
@permission_required('people.change_leaverequest',raise_exception=True)
def leave_decision(request,leave_id,status):
 enabled(request,'leaves')
 if status not in [LeaveRequest.Status.APPROVED,LeaveRequest.Status.REJECTED]:raise Http404
 with transaction.atomic():
  leave=get_object_or_404(LeaveRequest.objects.select_for_update(),pk=leave_id,company=request.company,status=LeaveRequest.Status.PENDING)
  if leave.employee.user_id==request.user.pk:raise PermissionDenied
  if status==LeaveRequest.Status.APPROVED and LeaveRequest.objects.filter(employee=leave.employee,status=LeaveRequest.Status.APPROVED,start_date__lte=leave.end_date,end_date__gte=leave.start_date).exists():messages.error(request,'Les dates chevauchent un congé déjà approuvé.')
  else:
   leave.status=status;leave.decided_by=request.user;leave.save(update_fields=['status','decided_by']);AuditLog.objects.create(actor=request.user,action=f'LEAVE_{status}',method='POST',path=request.path,status_code=200);messages.success(request,'Décision enregistrée.')
 return redirect('people:leaves')
@login_required
@require_active_company
@permission_required('people.view_attendance',raise_exception=True)
def attendance_list(request):
 enabled(request,'attendance');employee=scoped_employees(request).filter(user=request.user).first();records=Attendance.objects.filter(company=request.company).select_related('employee__user')
 if not request.user.has_perm('people.change_attendance') and employee:records=records.filter(employee=employee)
 if request.method=='POST':
  if not employee:messages.error(request,'Votre compte ne possède pas encore de dossier employé.')
  else:
   record=Attendance.objects.filter(employee=employee,work_date=request.POST.get('work_date')).first()
   form=AttendanceForm(request.POST,instance=record)
   if form.is_valid():
    record=form.save(commit=False);record.company=request.company;record.employee=employee
    try:record.full_clean();record.save()
    except ValidationError as ex:form.add_error(None,ex)
    else:messages.success(request,'Présence enregistrée.');return redirect('people:attendance')
   return render(request,'people/attendance.html',{'records':records,'form':form})
 form=AttendanceForm(initial={'work_date':timezone.localdate()});return render(request,'people/attendance.html',{'records':records[:100],'form':form})
@login_required
@require_active_company
@permission_required('people.add_expensereport',raise_exception=True)
def expense_list(request):
 enabled(request,'expenses');employee=scoped_employees(request).filter(user=request.user).first();expenses=ExpenseReport.objects.filter(company=request.company).select_related('employee__user')
 if not request.user.has_perm('people.change_expensereport') and employee:expenses=expenses.filter(employee=employee)
 if request.method=='POST':
  if not employee:messages.error(request,'Votre compte ne possède pas encore de dossier employé.')
  else:
   form=ExpenseForm(request.POST)
   if form.is_valid():
    expense=form.save(commit=False);expense.company=request.company;expense.employee=employee;expense.currency=request.company.currency
    try:expense.full_clean();expense.save()
    except ValidationError as ex:form.add_error(None,ex)
    else:messages.success(request,'Note de frais soumise pour validation.');return redirect('people:expenses')
   return render(request,'people/expenses.html',{'expenses':expenses,'form':form})
 form=ExpenseForm();return render(request,'people/expenses.html',{'expenses':expenses[:100],'form':form})
@login_required
@require_POST
@require_active_company
@permission_required('people.change_expensereport',raise_exception=True)
def expense_decision(request,expense_id,status):
 enabled(request,'expenses')
 if status not in [ExpenseReport.Status.APPROVED,ExpenseReport.Status.REJECTED]:raise Http404
 expense=get_object_or_404(ExpenseReport,pk=expense_id,company=request.company,status=ExpenseReport.Status.PENDING)
 if expense.employee.user_id==request.user.pk:raise PermissionDenied
 expense.status=status;expense.decided_by=request.user;expense.save(update_fields=['status','decided_by']);AuditLog.objects.create(actor=request.user,action=f'EXPENSE_{status}',method='POST',path=request.path,status_code=200)
 return redirect('people:expenses')
class PayslipForm(forms.ModelForm):
 class Meta:
  model=Payslip;fields=('employee','period_start','period_end','gross_amount','deductions')
  labels={'employee':'Collaborateur','period_start':'Début de période','period_end':'Fin de période','gross_amount':'Salaire brut','deductions':'Retenues manuelles'}
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs);self.fields['employee'].queryset=Employee.objects.filter(company=company,is_active=True)

@login_required
@require_active_company
@permission_required('people.view_payslip',raise_exception=True)
def payroll(request):
 enabled(request,'payroll');payslips=Payslip.objects.filter(company=request.company).select_related('employee__user')
 if not request.user.has_perm('people.change_payslip'):
  payslips=payslips.filter(employee__user=request.user)
 if request.method=='POST':
  if not request.user.has_perm('people.add_payslip'):raise PermissionDenied
  form=PayslipForm(request.POST,company=request.company)
  if form.is_valid():
   slip=form.save(commit=False);slip.company=request.company;slip.currency=request.company.currency;slip.created_by=request.user
   try:slip.full_clean();slip.save()
   except ValidationError as ex:form.add_error(None,ex)
   else:messages.success(request,'Bulletin de pré-paie créé.');return redirect('people:payroll')
 else:form=PayslipForm(company=request.company)
 return render(request,'people/payroll.html',{'payslips':payslips[:100],'form':form})
@login_required
@require_POST
@require_active_company
@permission_required('people.change_payslip',raise_exception=True)
def payslip_decision(request,slip_id,status):
 enabled(request,'payroll')
 if status not in [Payslip.Status.APPROVED,Payslip.Status.REJECTED]:raise Http404
 with transaction.atomic():
  slip=get_object_or_404(Payslip.objects.select_for_update(),pk=slip_id,company=request.company,status=Payslip.Status.DRAFT)
  if slip.employee.user_id==request.user.pk:raise PermissionDenied
  slip.status=status;slip.decided_by=request.user;slip.save(update_fields=['status','decided_by'])
 return redirect('people:payroll')
