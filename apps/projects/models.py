from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
class Project(models.Model):
 class Status(models.TextChoices): ACTIVE='ACTIVE','En cours'; DONE='DONE','Terminé'; CANCELLED='CANCELLED','Annulé'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='projects')
 name=models.CharField(max_length=180)
 description=models.TextField(blank=True)
 status=models.CharField(max_length=12,choices=Status.choices,default=Status.ACTIVE)
 start_date=models.DateField(default=timezone.localdate)
 due_date=models.DateField(null=True,blank=True)
 created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name='projects_created')
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta: ordering=['status','due_date','name']
 def __str__(self): return self.name
class ProjectTask(models.Model):
 class Status(models.TextChoices): TODO='TODO','À faire'; DOING='DOING','En cours'; DONE='DONE','Terminée'; BLOCKED='BLOCKED','Bloquée'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='project_tasks')
 project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name='tasks')
 title=models.CharField(max_length=180)
 description=models.TextField(blank=True)
 assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='project_tasks')
 status=models.CharField(max_length=10,choices=Status.choices,default=Status.TODO)
 due_date=models.DateField(null=True,blank=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta: ordering=['status','due_date','title']
 def __str__(self): return self.title
class TimeEntry(models.Model):
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='time_entries')
 task=models.ForeignKey(ProjectTask,on_delete=models.PROTECT,related_name='time_entries')
 user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='time_entries')
 work_date=models.DateField(default=timezone.localdate)
 hours=models.DecimalField(max_digits=5,decimal_places=2)
 description=models.CharField(max_length=255,blank=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:
  ordering=['-work_date','-created_at']
  constraints=[models.CheckConstraint(condition=Q(hours__gt=0,hours__lte=24),name='timesheet_hours_1_24')]
