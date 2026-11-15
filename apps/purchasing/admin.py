from django.contrib import admin
from apps.companies.models import CompanyMembership
from .models import PurchaseOrder
@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
 list_display=('number','supplier','product','quantity','unit_cost','currency','status','company','created_at')
 list_filter=('company','status','currency')
 search_fields=('number','supplier__name','product__name')
 readonly_fields=('number','company','supplier','product','quantity','unit_cost','currency','status','notes','created_by','created_at','updated_at')
 def has_add_permission(self,request):return False
 def has_change_permission(self,request,obj=None):return False
 def has_delete_permission(self,request,obj=None):return False
 def get_queryset(self,request):
  qs=super().get_queryset(request)
  if request.user.is_superuser:return qs
  ids=CompanyMembership.objects.filter(user=request.user,is_active=True).values('company_id')
  return qs.filter(company_id__in=ids)
