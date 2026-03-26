from django.contrib import admin
from .models import Utility, UtilityAccount, UtilityBill


@admin.register(Utility)
class UtilityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'display_name', 'icon_color', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'display_name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'display_name', 'icon_color')
        }),
        ('Details', {
            'fields': ('description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class UtilityBillInline(admin.TabularInline):
    model = UtilityBill
    extra = 0
    readonly_fields = ['bill_reference', 'created_at', 'is_overdue']
    fields = ['bill_reference', 'amount', 'bill_date', 'due_date', 'paid_date', 'status', 'is_overdue']


@admin.register(UtilityAccount)
class UtilityAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'unit', 'utility', 'account_number', 'status', 'current_balance', 'is_overdue']
    list_filter = ['status', 'utility', 'connected_at']
    search_fields = ['account_number', 'unit__unit_number', 'unit__property__name']
    readonly_fields = ['connected_at', 'updated_at', 'days_until_due', 'is_overdue']
    inlines = [UtilityBillInline]

    fieldsets = (
        ('Account Details', {
            'fields': ('unit', 'utility', 'account_number', 'account_name', 'provider')
        }),
        ('Status', {
            'fields': ('status', 'connected_by', 'last_updated_by')
        }),
        ('Financial Info', {
            'fields': ('current_balance', 'last_bill_amount', 'bill_due_date', 'days_until_due', 'is_overdue')
        }),
        ('Timestamps', {
            'fields': ('connected_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UtilityBill)
class UtilityBillAdmin(admin.ModelAdmin):
    list_display = ['id', 'bill_reference', 'account', 'amount', 'status', 'bill_date', 'due_date', 'is_overdue']
    list_filter = ['status', 'bill_date', 'due_date']
    search_fields = ['bill_reference', 'account__account_number']
    readonly_fields = ['created_at', 'is_overdue']

    fieldsets = (
        ('Bill Details', {
            'fields': ('account', 'bill_reference', 'amount', 'status')
        }),
        ('Dates', {
            'fields': ('bill_date', 'due_date', 'paid_date', 'is_overdue')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_at'),
            'classes': ('collapse',)
        }),
    )
