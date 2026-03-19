from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering        = ['phone']
    list_display    = [
        'phone', 'first_name', 'last_name',
        'role', 'kyc_tier', 'phone_verified',
        'nin_verified', 'bvn_verified', 'is_active'
    ]
    list_filter     = ['role', 'kyc_tier', 'is_active', 'phone_verified']
    search_fields   = ['phone', 'first_name', 'last_name']

    fieldsets = (
        ('Identity', {
            'fields': ('phone', 'email', 'password')
        }),
        ('Personal', {
            'fields': ('first_name', 'last_name')
        }),
        ('Role', {
            'fields': ('role',)
        }),
        ('Verification', {
            'fields': (
                'phone_verified',
                'nin_verified',
                'bvn_verified',
                'nin',
                'bvn',
            )
        }),
        ('KYC', {
            'fields': (
                'kyc_tier',
                'address_line1',
                'address_line2',
                'lga',
                'state',
            )
        }),
        ('Tier 3 Details', {
            'fields': (
                'employer_name',
                'monthly_income',
                'nok_name',
                'nok_phone',
                'nok_relationship',
            )
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'phone', 'first_name', 'last_name',
                'password1', 'password2',
            ),
        }),
    )