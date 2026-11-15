from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Informations ERP", {"fields": ("phone",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Informations ERP", {"fields": ("email", "phone")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
