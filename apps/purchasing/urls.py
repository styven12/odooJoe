from django.urls import path
from . import views
app_name='purchasing'
urlpatterns=[path('',views.order_list,name='orders'),path('new/',views.create_order,name='create_order'),path('<int:order_id>/<str:action>/',views.order_action,name='action')]
