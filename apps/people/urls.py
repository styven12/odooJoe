from django.urls import path
from . import views
app_name='people'
urlpatterns=[path('employees/',views.employee_list,name='employees'),path('leaves/',views.leave_list,name='leaves'),path('leaves/<int:leave_id>/<str:status>/',views.leave_decision,name='leave_decision'),path('attendance/',views.attendance_list,name='attendance'),path('expenses/',views.expense_list,name='expenses'),path('expenses/<int:expense_id>/<str:status>/',views.expense_decision,name='expense_decision'),path('payroll/',views.payroll,name='payroll'),path('payroll/<int:slip_id>/<str:status>/',views.payslip_decision,name='payslip_decision')]
