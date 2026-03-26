from rest_framework import serializers
from .models import Utility, UtilityAccount, UtilityBill


class UtilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Utility
        fields = ['id', 'name', 'display_name', 'icon_color', 'description', 'is_active']


class UtilityBillSerializer(serializers.ModelSerializer):
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = UtilityBill
        fields = [
            'id', 'bill_reference', 'amount', 'status',
            'bill_date', 'due_date', 'paid_date', 'is_overdue', 'notes'
        ]

    def get_is_overdue(self, obj):
        return obj.is_overdue


class UtilityAccountSerializer(serializers.ModelSerializer):
    utility = UtilitySerializer(read_only=True)
    utility_id = serializers.IntegerField(write_only=True)
    bills = UtilityBillSerializer(many=True, read_only=True)
    is_overdue = serializers.SerializerMethodField()
    days_until_due = serializers.SerializerMethodField()

    class Meta:
        model = UtilityAccount
        fields = [
            'id', 'utility', 'utility_id', 'account_number', 'account_name',
            'provider', 'status', 'current_balance', 'last_bill_amount',
            'bill_due_date', 'connected_at', 'is_overdue', 'days_until_due', 'bills'
        ]
        read_only_fields = ['id', 'connected_at']

    def get_is_overdue(self, obj):
        return obj.is_overdue

    def get_days_until_due(self, obj):
        return obj.days_until_due
