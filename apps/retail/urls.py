from django.urls import path
from . import views
app_name='retail'
urlpatterns=[path('pos/',views.pos,name='pos'),path('shop/',views.webshop,name='webshop'),path('shop/<int:order_id>/confirm/',views.confirm_web_order,name='confirm_web_order')]
