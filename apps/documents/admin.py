from django.contrib import admin
from apps.companies.models import CompanyMembership
from .models import DocumentRecord
@admin.register(DocumentRecord)
class DocumentAdmin(admin.ModelAdmin):
 list_display=('title','category','company','original_name','size_bytes','uploaded_by','uploaded_at');list_filter=('company','category');search_fields=('title','original_name')
 def get_queryset(self,request):
  qs=super().get_queryset(request)
  if request.user.is_superuser:return qs
  allowed=CompanyMembership.objects.filter(user=request.user,is_active=True).values('company_id');return qs.filter(company_id__in=allowed)
 def has_delete_permission(self,request,obj=None):return False
 def has_add_permission(self,request):return False
 def has_change_permission(self,request,obj=None):return False
