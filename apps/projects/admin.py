from django.contrib import admin
from apps.companies.models import CompanyMembership
from .models import Project,ProjectTask,TimeEntry
class CompanyAdmin(admin.ModelAdmin):
 def get_queryset(self,request):
  qs=super().get_queryset(request)
  if request.user.is_superuser:return qs
  allowed=CompanyMembership.objects.filter(user=request.user,is_active=True).values('company_id')
  return qs.filter(company_id__in=allowed)
 def formfield_for_foreignkey(self,db_field,request,**kwargs):
  if not request.user.is_superuser:
   allowed=CompanyMembership.objects.filter(user=request.user,is_active=True).values('company_id')
   if db_field.name=='project':kwargs['queryset']=Project.objects.filter(company_id__in=allowed)
   if db_field.name=='task':kwargs['queryset']=ProjectTask.objects.filter(company_id__in=allowed)
   if db_field.name=='assigned_to' or db_field.name=='user':kwargs['queryset']=db_field.remote_field.model.objects.filter(company_memberships__company_id__in=allowed,company_memberships__is_active=True).distinct()
  return super().formfield_for_foreignkey(db_field,request,**kwargs)
@admin.register(Project)
class ProjectAdmin(CompanyAdmin):
 list_display=('name','company','status','start_date','due_date')
 list_filter=('company','status')
 search_fields=('name','description')
 def has_add_permission(self,request):return False
 def has_change_permission(self,request,obj=None):return False
 def has_delete_permission(self,request,obj=None):return False
@admin.register(ProjectTask)
class TaskAdmin(CompanyAdmin):
 list_display=('title','project','company','assigned_to','status','due_date')
 list_filter=('company','status')
 search_fields=('title','project__name')
 def has_add_permission(self,request):return False
 def has_change_permission(self,request,obj=None):return False
 def has_delete_permission(self,request,obj=None):return False
@admin.register(TimeEntry)
class TimeEntryAdmin(CompanyAdmin):
 list_display=('work_date','user','task','company','hours')
 list_filter=('company','work_date')
 search_fields=('task__title','task__project__name','user__username')
 readonly_fields=('company','task','user','work_date','hours','description','created_at')
 def has_add_permission(self,request): return False
 def has_change_permission(self,request,obj=None): return False
 def has_delete_permission(self,request,obj=None): return False
