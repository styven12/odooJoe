from django.urls import path
from . import views
app_name='production'
urlpatterns=[path('manufacturing/',views.manufacturing,name='manufacturing'),path('manufacturing/bom/',views.create_bom,name='create_bom'),path('manufacturing/new/',views.create_mo,name='create_mo'),path('manufacturing/<int:order_id>/<str:action>/',views.mo_action,name='mo_action'),path('shipping/',views.shipments,name='shipments'),path('shipping/<int:shipment_id>/<str:state>/',views.shipment_action,name='shipment_action')]
