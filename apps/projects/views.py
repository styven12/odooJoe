from django import forms
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from apps.core.models import ERPModule
from apps.core.guards import require_active_company
from .models import Project,ProjectTask,TimeEntry

def enabled(request,slug):
 if not ERPModule.objects.filter(slug=slug,is_enabled=True).exists(): raise Http404('Module désactivé')
 # Sans société active : les GET affichent des listes vides ; les POST sont
 # redirigés avec un message par @require_active_company.
class ProjectForm(forms.ModelForm):
 class Meta: model=Project; fields=('name','description','start_date','due_date')
class TaskForm(forms.ModelForm):
 class Meta: model=ProjectTask; fields=('title','assigned_to','due_date')
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs); self.fields['assigned_to'].queryset=get_user_model().objects.filter(company_memberships__company=company,company_memberships__is_active=True,is_active=True).distinct()
class TimeEntryForm(forms.ModelForm):
 class Meta:
  model=TimeEntry; fields=('task','work_date','hours','description')
  labels={'task':'Tâche','work_date':'Date','hours':'Heures','description':'Description'}
 def __init__(self,*args,company,**kwargs):
  super().__init__(*args,**kwargs); self.fields['task'].queryset=ProjectTask.objects.filter(company=company,project__status=Project.Status.ACTIVE)
@login_required
@permission_required('projects.view_project',raise_exception=True)
def project_list(request):
 enabled(request,'projects'); projects=Project.objects.filter(company=request.company).prefetch_related('tasks__assigned_to')
 members=request.company.memberships.filter(is_active=True,user__is_active=True).select_related('user') if request.company else []
 return render(request,'projects/list.html',{'projects':projects,'members':members})
@login_required
@require_POST
@require_active_company
@permission_required('projects.add_project',raise_exception=True)
def create_project(request):
 enabled(request,'projects'); form=ProjectForm(request.POST)
 if form.is_valid():
  p=form.save(commit=False); p.company=request.company; p.created_by=request.user
  try:p.full_clean();p.save()
  except ValidationError as e:messages.error(request,str(e))
  else:messages.success(request,'Projet créé.')
 else:messages.error(request,form.errors.as_text())
 return redirect('projects:list')
@login_required
@require_POST
@require_active_company
@permission_required('projects.add_projecttask',raise_exception=True)
def create_task(request,project_id):
 enabled(request,'projects'); project=get_object_or_404(Project,pk=project_id,company=request.company,status=Project.Status.ACTIVE); form=TaskForm(request.POST,company=request.company)
 if form.is_valid():
  task=form.save(commit=False);task.project=project;task.company=request.company;task.save();messages.success(request,'Tâche créée.')
 else:messages.error(request,form.errors.as_text())
 return redirect('projects:list')
@login_required
@require_active_company
@permission_required('projects.view_timeentry',raise_exception=True)
def timesheets(request):
 enabled(request,'timesheets'); entries=TimeEntry.objects.filter(company=request.company).select_related('task','task__project','user')
 if not request.user.has_perm('projects.change_timeentry'):entries=entries.filter(user=request.user)
 totals=entries.values('user__username').annotate(hours=Sum('hours'))
 if request.method=='POST':
  form=TimeEntryForm(request.POST,company=request.company)
  if form.is_valid():
   entry=form.save(commit=False);entry.company=request.company;entry.user=request.user;entry.save();messages.success(request,'Temps enregistré.');return redirect('projects:timesheets')
 else:form=TimeEntryForm(company=request.company)
 return render(request,'projects/timesheets.html',{'entries':entries[:100],'form':form,'totals':totals})
@login_required
@require_POST
@require_active_company
@permission_required('projects.change_projecttask',raise_exception=True)
def task_status(request,task_id,status):
 enabled(request,'projects');task=get_object_or_404(ProjectTask,pk=task_id,company=request.company)
 if status not in ProjectTask.Status.values: raise Http404
 task.status=status;task.save(update_fields=['status']);return redirect('projects:list')
