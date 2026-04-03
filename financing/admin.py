from django.contrib import admin
from .models import (
    RentAdvance, RentAdvanceRepayment,
    UtilityAdvance, UtilityAdvanceRepayment,
    CreditBuilderLoan, CreditBuilderRepayment,
)


class RentAdvanceRepaymentInline(admin.TabularInline):
    model  = RentAdvanceRepayment
    extra  = 0
    fields = ['instalment_number', 'amount', 'due_date', 'status', 'reported_to_bureau']
    readonly_fields = ['instalment_number']


@admin.register(RentAdvance)
class RentAdvanceAdmin(admin.ModelAdmin):
    list_display  = ['tenant', 'amount_approved', 'repayment_months', 'status', 'created_at']
    list_filter   = ['status', 'repayment_months']
    search_fields = ['tenant__phone']
    readonly_fields = ['id', 'created_at']
    inlines       = [RentAdvanceRepaymentInline]


class UtilityRepaymentInline(admin.TabularInline):
    model  = UtilityAdvanceRepayment
    extra  = 0
    fields = ['instalment_number', 'amount', 'due_date', 'status']


@admin.register(UtilityAdvance)
class UtilityAdvanceAdmin(admin.ModelAdmin):
    list_display  = ['tenant', 'utility_type', 'provider_name', 'amount_requested', 'status']
    list_filter   = ['status', 'utility_type']
    search_fields = ['tenant__phone', 'provider_name']
    inlines       = [UtilityRepaymentInline]


class CreditBuilderRepaymentInline(admin.TabularInline):
    model  = CreditBuilderRepayment
    extra  = 0
    fields = ['instalment_number', 'monthly_total', 'due_date', 'status', 'reported_to_bureau']


@admin.register(CreditBuilderLoan)
class CreditBuilderLoanAdmin(admin.ModelAdmin):
    list_display  = ['tenant', 'loan_amount', 'plan_months', 'status', 'score_at_start', 'score_current']
    list_filter   = ['status', 'plan_months']
    search_fields = ['tenant__phone']
    inlines       = [CreditBuilderRepaymentInline]