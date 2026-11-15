from django.urls import path
from . import views
app_name='service'
urlpatterns=[path('assets/',views.assets,name='assets'),path('maintenance/',views.maintenance,name='maintenance'),path('maintenance/<int:job_id>/<str:state>/',views.maintenance_status,name='maintenance_status'),path('tickets/',views.tickets,name='tickets'),path('tickets/<int:ticket_id>/<str:state>/',views.ticket_status,name='ticket_status')]
