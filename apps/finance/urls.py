from django.urls import path
from . import views
app_name='finance'
urlpatterns=[path('accounting/',views.accounting,name='accounting'),path('accounting/accounts/',views.create_account,name='create_account'),path('accounting/entries/',views.create_entry,name='create_entry'),path('accounting/entries/<int:entry_id>/post/',views.post_entry,name='post_entry'),path('treasury/',views.treasury,name='treasury'),path('treasury/accounts/',views.create_treasury_account,name='create_treasury_account'),path('treasury/movements/',views.create_treasury_movement,name='create_treasury_movement')]
