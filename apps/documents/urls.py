from django.urls import path
from . import views
app_name='documents'
urlpatterns=[path('',views.library,name='library'),path('<int:document_id>/download/',views.download,name='download')]
