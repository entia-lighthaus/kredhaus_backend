from django.contrib import admin
from .models import Wallet, SavingsPocket, Transaction, VirtualAccount


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display  = ['user', 'currency', 'balance', 'virtual_account_number', 'is_active']
    list_filter   = ['currency', 'is_active']
    search_fields = ['user__phone', 'virtual_account_number']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(SavingsPocket)
class SavingsPocketAdmin(admin.ModelAdmin):
    list_display  = ['name', 'wallet', 'pocket_type', 'balance', 'target_amount', 'is_locked']
    list_filter   = ['pocket_type', 'is_locked']
    search_fields = ['wallet__user__phone', 'name']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display  = ['reference', 'wallet', 'transaction_type', 'amount', 'currency', 'status', 'created_at']
    list_filter   = ['transaction_type', 'status', 'currency']
    search_fields = ['reference', 'wallet__user__phone']
    readonly_fields = ['id', 'created_at']


@admin.register(VirtualAccount)
class VirtualAccountAdmin(admin.ModelAdmin):
    list_display  = ['account_number', 'bank_name', 'account_name', 'wallet']
    search_fields = ['account_number', 'wallet__user__phone']