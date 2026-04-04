# financing/serializers.py
# This module defines serializers for our financing products, including rent advances, utility advances, and credit builder loans.
# These serializers handle the conversion of complex model instances into JSON representations for API responses, 
# as well as validating and deserializing incoming data for creating new advances and loans.

from rest_framework import serializers
from .models import (
    RentAdvance, RentAdvanceRepayment,
    UtilityAdvance, UtilityAdvanceRepayment,
    CreditBuilderLoan, CreditBuilderRepayment,
)


# ── Rent Advance ───────────────────────────────────────────────────────────

class RentAdvanceRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RentAdvanceRepayment
        fields = [
            'id',
            'instalment_number',
            'amount',
            'due_date',
            'paid_date',
            'status',
            'reported_to_bureau',
        ]
        read_only_fields = fields


# The RentAdvanceSerializer includes a nested representation of the repayment schedule, as well as read-only fields that calculate the total amount repaid, remaining balance, and payment progress.
class RentAdvanceSerializer(serializers.ModelSerializer):
    repayments       = RentAdvanceRepaymentSerializer(many=True, read_only=True)
    amount_repaid    = serializers.ReadOnlyField()
    amount_remaining = serializers.ReadOnlyField()
    payments_made    = serializers.ReadOnlyField()
    payments_total   = serializers.ReadOnlyField()

    class Meta:
        model  = RentAdvance
        fields = [
            'id',
            'amount_requested',
            'amount_approved',
            'repayment_months',
            'flat_fee_percent',
            'flat_fee_amount',
            'total_repayable',
            'monthly_repayment',
            'status',
            'disbursed_at',
            'completed_at',
            'amount_repaid',
            'amount_remaining',
            'payments_made',
            'payments_total',
            'repayments',
            'created_at',
        ]
        read_only_fields = fields


class RentAdvanceCreateSerializer(serializers.Serializer):
    lease_id          = serializers.IntegerField()
    amount_requested  = serializers.DecimalField(max_digits=12, decimal_places=2)
    repayment_months  = serializers.ChoiceField(choices=['3', '6', '9'])

    def validate_amount_requested(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Amount must be greater than zero.'
            )
        return value


# ── Utility Advance ────────────────────────────────────────────────────────

class UtilityAdvanceRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UtilityAdvanceRepayment
        fields = [
            'id',
            'instalment_number',
            'amount',
            'due_date',
            'paid_date',
            'status',
        ]
        read_only_fields = fields


class UtilityAdvanceSerializer(serializers.ModelSerializer):
    repayments = UtilityAdvanceRepaymentSerializer(many=True, read_only=True)

    class Meta:
        model  = UtilityAdvance
        fields = [
            'id',
            'utility_type',
            'provider_name',
            'account_number',
            'amount_requested',
            'flat_fee_percent',
            'flat_fee_amount',
            'total_repayable',
            'repayment_months',
            'monthly_repayment',
            'status',
            'disbursed_at',
            'completed_at',
            'repayments',
            'created_at',
        ]
        read_only_fields = fields


class UtilityAdvanceCreateSerializer(serializers.Serializer):
    utility_type      = serializers.ChoiceField(
        choices=['electricity', 'gas', 'water', 'internet']
    )
    provider_name     = serializers.CharField(max_length=64)
    account_number    = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
    )
    amount_requested  = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    repayment_months  = serializers.ChoiceField(choices=['1', '2', '3'])

    def validate_amount_requested(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Amount must be greater than zero.'
            )
        if value > 50000:
            raise serializers.ValidationError(
                'Maximum utility advance is ₦50,000.'
            )
        return value


# ── Credit Builder ─────────────────────────────────────────────────────────

class CreditBuilderRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CreditBuilderRepayment
        fields = [
            'id',
            'instalment_number',
            'principal_amount',
            'fee_amount',
            'monthly_total',
            'due_date',
            'paid_date',
            'status',
            'reported_to_bureau',
        ]
        read_only_fields = fields


class CreditBuilderLoanSerializer(serializers.ModelSerializer):
    repayments         = CreditBuilderRepaymentSerializer(many=True, read_only=True)
    payments_made      = serializers.ReadOnlyField()
    payments_remaining = serializers.ReadOnlyField()
    amount_repaid      = serializers.ReadOnlyField()
    interest_earned_on_vault = serializers.ReadOnlyField()

    class Meta:
        model  = CreditBuilderLoan
        fields = [
            'id',
            'loan_amount',
            'plan_months',
            'monthly_fee',
            'monthly_principal',
            'monthly_total',
            'total_fees',
            'total_repayable',
            'score_at_start',
            'score_current',
            'status',
            'started_at',
            'completed_at',
            'payments_made',
            'payments_remaining',
            'amount_repaid',
            'interest_earned_on_vault',
            'repayments',
        ]
        read_only_fields = fields


class CreditBuilderCreateSerializer(serializers.Serializer):
    loan_amount  = serializers.ChoiceField(
        choices=[50000, 100000, 150000, 200000]
    )
    plan_months  = serializers.ChoiceField(choices=['6', '12'])