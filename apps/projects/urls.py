from django.urls import path
from . import views
app_name='projects'
urlpatterns=[path('',views.project_list,name='list'),path('new/',views.create_project,name='create'),path('timesheets/',views.timesheets,name='timesheets'),path('<int:project_id>/tasks/new/',views.create_task,name='create_task'),path('tasks/<int:task_id>/<str:status>/',views.task_status,name='task_status')]
