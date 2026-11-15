from django.contrib import admin
from apps.companies.models import CompanyMembership
from .models import Product,StockMovement
class CompanyAdmin(admin.ModelAdmin):
 def get_queryset(self,request):
  qs=super().get_queryset(request)
  if request.user.is_superuser:return qs
  ids=CompanyMembership.objects.filter(user=request.user,is_active=True).values('company_id')
  return qs.filter(company_id__in=ids)
 def formfield_for_foreignkey(self,db_field,request,**kwargs):
  if not request.user.is_superuser:
   ids=CompanyMembership.objects.filter(user=request.user,is_active=True).values('company_id')
   if db_field.name=='company':kwargs['queryset']=db_field.remote_field.model.objects.filter(pk__in=ids)
   if db_field.name=='product':kwargs['queryset']=db_field.remote_field.model.objects.filter(company_id__in=ids)
  return super().formfield_for_foreignkey(db_field,request,**kwargs)
@admin.register(Product)
class ProductAdmin(CompanyAdmin):
 list_display=('sku','name','company','unit','reorder_level','is_active')
 list_filter=('company','is_active')
 search_fields=('sku','name')
 def has_add_permission(self,request):return False
 def has_change_permission(self,request,obj=None):return False
 def has_delete_permission(self,request,obj=None):return False
@admin.register(StockMovement)
class StockMovementAdmin(CompanyAdmin):
 list_display=('created_at','product','kind','quantity','company','reference','created_by')
 list_filter=('company','kind','created_at')
 search_fields=('product__sku','product__name','reference')
 readonly_fields=('created_at','created_by')
 def has_add_permission(self,request): return False
 def has_change_permission(self,request,obj=None): return False
 def has_delete_permission(self,request,obj=None): return False
