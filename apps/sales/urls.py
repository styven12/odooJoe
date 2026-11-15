from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("", views.order_list, name="orders"),
    path("export.csv", views.export_orders, name="export_orders"),
    path("opportunities/<int:opportunity_id>/quote/", views.create_quote, name="create_quote"),
    path("<int:order_id>/confirm/", views.confirm_order, name="confirm_order"),
    path("invoices/", views.invoice_list, name="invoices"),
    path("invoices/export.csv", views.export_invoices, name="export_invoices"),
    path("invoices/<int:invoice_id>/pay/", views.mark_invoice_paid, name="pay_invoice"),
]
