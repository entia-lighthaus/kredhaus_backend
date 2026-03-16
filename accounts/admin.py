from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering        = ['phone']
    list_display    = ['phone', 'first_name', 'last_name', 'role', 'is_active']
    list_filter     = ['role', 'is_active']
    search_fields   = ['phone', 'first_name', 'last_name']

    fieldsets = (
        ('Identity',   {'fields': ('phone', 'email', 'password')}),
        ('Personal',   {'fields': ('first_name', 'last_name')}),
        ('Role',       {'fields': ('role',)}),
        ('Permissions',{'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields':  ('phone', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )