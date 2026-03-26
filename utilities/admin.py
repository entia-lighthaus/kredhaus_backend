from django.contrib import admin
from .models import (
    Utility, UtilityAccount, UtilityBill,
    UtilityRate, UtilityMeterProvider, UtilityMeterReading, UtilityUsageRecord
)


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


@admin.register(UtilityRate)
class UtilityRateAdmin(admin.ModelAdmin):
    list_display = ['id', 'utility', 'band', 'unit', 'rate', 'fixed_charge', 'is_current', 'effective_from']
    list_filter = ['is_active', 'effective_from', 'utility', 'band']
    search_fields = ['utility__display_name']
    readonly_fields = ['created_at', 'is_current']

    fieldsets = (
        ('Utility & Band', {
            'fields': ('utility', 'band', 'unit')
        }),
        ('Pricing', {
            'fields': ('rate', 'fixed_charge', 'min_consumption', 'max_consumption')
        }),
        ('Validity', {
            'fields': ('effective_from', 'effective_to', 'is_active', 'is_current')
        }),
        ('Additional', {
            'fields': ('notes', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UtilityMeterProvider)
class UtilityMeterProviderAdmin(admin.ModelAdmin):
    list_display = ['id', 'account', 'method', 'reading_type', 'is_active', 'last_reading_date']
    list_filter = ['method', 'reading_type', 'is_active']
    search_fields = ['account__account_number', 'provider_name']
    readonly_fields = ['last_sync_attempt', 'created_at', 'updated_at']

    fieldsets = (
        ('Account', {
            'fields': ('account',)
        }),
        ('Data Source Configuration', {
            'fields': ('method', 'reading_type', 'tariff_band', 'manual_frequency')
        }),
        ('Smart Meter Settings', {
            'fields': ('provider_name', 'api_key', 'webhook_token'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'last_reading_date', 'last_sync_attempt')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class UtilityUsageRecordInline(admin.TabularInline):
    model = UtilityUsageRecord
    extra = 0
    readonly_fields = ['consumption', 'unit', 'period_start', 'period_end', 'amount_due', 'created_at']
    fields = ['consumption', 'unit', 'period_start', 'period_end', 'unit_rate', 'amount_due', 'is_billed']
    can_delete = False


@admin.register(UtilityMeterReading)
class UtilityMeterReadingAdmin(admin.ModelAdmin):
    list_display = ['id', 'account', 'reading_date', 'source', 'tariff_band', 'calculated_consumption', 'is_processed', 'is_confirmed']
    list_filter = ['source', 'reading_date', 'is_processed', 'is_confirmed']
    search_fields = ['account__account_number', 'submitted_by']
    readonly_fields = ['calculated_consumption', 'created_at']
    inlines = [UtilityUsageRecordInline]

    fieldsets = (
        ('Account & Date', {
            'fields': ('account', 'reading_date')
        }),
        ('Meter Readings', {
            'fields': ('previous_reading', 'current_reading')
        }),
        ('Direct Consumption', {
            'fields': ('consumption', 'calculated_consumption')
        }),
        ('Source & Submission', {
            'fields': ('source', 'tariff_band', 'submitted_by', 'notes')
        }),
        ('Status', {
            'fields': ('is_processed', 'is_confirmed')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UtilityUsageRecord)
class UtilityUsageRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'account', 'consumption', 'unit', 'period_end', 'amount_due', 'is_billed']
    list_filter = ['is_billed', 'period_end', 'unit']
    search_fields = ['account__account_number']
    readonly_fields = ['meter_reading', 'account', 'consumption', 'unit', 'created_at', 'cost_breakdown_display']
    can_delete = False

    fieldsets = (
        ('Account & Meter Reading', {
            'fields': ('meter_reading', 'account')
        }),
        ('Consumption', {
            'fields': ('consumption', 'unit')
        }),
        ('Billing Period', {
            'fields': ('period_start', 'period_end')
        }),
        ('Cost Breakdown', {
            'fields': ('unit_rate', 'variable_cost', 'fixed_charge', 'amount_due', 'cost_breakdown_display')
        }),
        ('Status', {
            'fields': ('is_billed',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def cost_breakdown_display(self, obj):
        """Display cost breakdown in admin."""
        breakdown = obj.cost_breakdown
        return f"""
        Consumption: {breakdown['consumption']} {breakdown['unit']}<br/>
        Unit Rate: ₦{breakdown['unit_rate']}<br/>
        Variable Cost: ₦{breakdown['variable_cost']}<br/>
        Fixed Charge: ₦{breakdown['fixed_charge']}<br/>
        <strong>Total: ₦{breakdown['total_amount_due']}</strong>
        """
    cost_breakdown_display.short_description = 'Cost Breakdown'

    def has_add_permission(self, request):
        """Usage records are created automatically from meter readings."""
        return False


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

