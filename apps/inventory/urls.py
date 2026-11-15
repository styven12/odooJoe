from django.urls import path
from . import views
app_name='inventory'
urlpatterns=[path('',views.stock_list,name='stock'),path('products/create/',views.create_product,name='create_product'),path('movements/create/',views.move_stock,name='move_stock')]
