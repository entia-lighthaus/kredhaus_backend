from rest_framework import serializers
from django.utils import timezone
from .models import (
    Utility, UtilityAccount, UtilityBill,
    UtilityRate, UtilityMeterProvider, UtilityMeterReading, UtilityUsageRecord,
    Supplier, SupplierService, SupplierAvailability, SupplierServiceRequest,
    SupplierMessage, SupplierRating
)


class UtilityRateSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UtilityRate
        fields = [
            'id', 'utility', 'band', 'unit', 'rate', 'fixed_charge',
            'min_consumption', 'max_consumption',
            'effective_from', 'effective_to', 'is_active', 'is_current'
        ]

    def get_is_current(self, obj):
        return obj.is_current


class UtilitySerializer(serializers.ModelSerializer):
    rates = UtilityRateSerializer(many=True, read_only=True)

    class Meta:
        model = Utility
        fields = ['id', 'name', 'display_name', 'icon_color', 'description', 'is_active', 'rates']


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


class UtilityMeterProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = UtilityMeterProvider
        fields = [
            'id', 'method', 'reading_type', 'tariff_band', 'provider_name',
            'manual_frequency', 'is_active', 'last_reading_date'
        ]
        read_only_fields = ['id']


class UtilityUsageRecordSerializer(serializers.ModelSerializer):
    cost_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = UtilityUsageRecord
        fields = [
            'id', 'consumption', 'unit', 'period_start', 'period_end',
            'unit_rate', 'variable_cost', 'fixed_charge', 'amount_due',
            'is_billed', 'cost_breakdown'
        ]
        read_only_fields = ['id']

    def get_cost_breakdown(self, obj):
        return obj.cost_breakdown


class UtilityMeterReadingSerializer(serializers.ModelSerializer):
    calculated_consumption = serializers.SerializerMethodField()
    estimated_bill = serializers.SerializerMethodField()
    usage_record = UtilityUsageRecordSerializer(read_only=True)
    account_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UtilityMeterReading
        fields = [
            'id', 'account_id', 'previous_reading', 'current_reading', 'consumption',
            'reading_date', 'source', 'tariff_band', 'is_processed', 'is_confirmed',
            'submitted_by', 'notes', 'calculated_consumption',
            'estimated_bill', 'usage_record'
        ]
        read_only_fields = ['id', 'is_processed', 'is_confirmed']

    def get_calculated_consumption(self, obj):
        """Show calculated consumption to tenant before confirming."""
        return float(obj.calculated_consumption)

    def get_estimated_bill(self, obj):
        """Show estimated amount they'll pay."""
        account = obj.account
        consumption = obj.calculated_consumption
        rate = None

        # First priority: explicit tariff band on reading
        if obj.tariff_band:
            rate = account.utility.rates.filter(
                band=obj.tariff_band,
                is_active=True,
                effective_from__lte=timezone.now().date(),
            ).order_by('-effective_from').first()

        # Second priority: per-account provider tariff band
        if not rate and hasattr(account, 'meter_provider') and account.meter_provider.tariff_band:
            rate = account.utility.rates.filter(
                band=account.meter_provider.tariff_band,
                is_active=True,
                effective_from__lte=timezone.now().date(),
            ).order_by('-effective_from').first()

        # Fallback: any current active band that fits consumption
        if not rate:
            rates = account.utility.rates.filter(
                is_active=True,
                effective_from__lte=timezone.now().date(),
            ).order_by('-effective_from')
            for candidate in rates:
                if candidate.contains_consumption(consumption):
                    rate = candidate
                    break
            if not rate and rates.exists():
                rate = rates.first()

        if not rate:
            return None

        variable = consumption * rate.rate
        total = variable + rate.fixed_charge

        return {
            'consumption': float(consumption),
            'unit': rate.unit,
            'band': rate.band,
            'unit_rate': float(rate.rate),
            'variable_cost': float(variable),
            'fixed_charge': float(rate.fixed_charge),
            'estimated_total': float(total),
        }


class UtilityAccountSerializer(serializers.ModelSerializer):
    utility = UtilitySerializer(read_only=True)
    utility_id = serializers.IntegerField(write_only=True)
    unit_id = serializers.IntegerField(write_only=True)
    bills = UtilityBillSerializer(many=True, read_only=True)
    meter_provider = UtilityMeterProviderSerializer(read_only=True)
    usage_records = UtilityUsageRecordSerializer(many=True, read_only=True)
    is_overdue = serializers.SerializerMethodField()
    days_until_due = serializers.SerializerMethodField()

    class Meta:
        model = UtilityAccount
        fields = [
            'id', 'utility', 'utility_id', 'unit_id', 'account_number', 'account_name',
            'provider', 'status', 'current_balance', 'last_bill_amount',
            'bill_due_date', 'connected_at', 'is_overdue', 'days_until_due',
            'bills', 'meter_provider', 'usage_records'
        ]
        read_only_fields = ['id', 'connected_at']

    def get_is_overdue(self, obj):
        return obj.is_overdue

    def get_days_until_due(self, obj):
        return obj.days_until_due


# ── Supplier Serializers ──────────────────────────────────────────────────

class SupplierServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierService
        fields = ['id', 'name', 'description', 'price', 'quantity', 'is_available']
        read_only_fields = ['id']


class SupplierAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierAvailability
        fields = ['is_online', 'current_orders', 'max_daily_orders', 'last_updated']
        read_only_fields = ['last_updated']


class SupplierRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierRating
        fields = [
            'id', 'rating', 'review_text', 'cleanliness', 'professionalism',
            'timeliness', 'reviewer_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SupplierDetailSerializer(serializers.ModelSerializer):
    """Full supplier detail with services and ratings."""
    services       = SupplierServiceSerializer(many=True, read_only=True)
    availability   = SupplierAvailabilitySerializer(read_only=True)
    ratings        = SupplierRatingSerializer(many=True, read_only=True)

    class Meta:
        model = Supplier
        fields = [
            'id', 'company_name', 'description', 'logo', 'icon_color',
            'phone_number', 'email', 'address', 'city',
            'average_rating', 'total_reviews', 'status', 'is_available',
            'pickup_time_minutes', 'delivery_fee', 'is_safety_certified',
            'services', 'availability', 'ratings', 'created_at'
        ]
        read_only_fields = ['id', 'average_rating', 'total_reviews', 'created_at']


class SupplierListSerializer(serializers.ModelSerializer):
    """Summary view of suppliers for listing."""
    class Meta:
        model = Supplier
        fields = [
            'id', 'company_name', 'logo', 'icon_color', 'phone_number',
            'average_rating', 'total_reviews', 'is_available',
            'pickup_time_minutes', 'delivery_fee', 'is_safety_certified'
        ]
        read_only_fields = ['id']


class SupplierMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierMessage
        fields = [
            'id', 'service_request', 'sender_type', 'sender_name', 'message_text',
            'attachment_url', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'service_request': {'write_only': True}
        }


class SupplierServiceRequestSerializer(serializers.ModelSerializer):
    """Full service request with nested messages."""
    messages        = SupplierMessageSerializer(many=True, read_only=True)
    supplier        = SupplierListSerializer(read_only=True)
    service         = SupplierServiceSerializer(read_only=True)
    
    supplier_id     = serializers.IntegerField(write_only=True)
    service_id      = serializers.IntegerField(write_only=True)
    unit_id         = serializers.IntegerField(write_only=True)

    class Meta:
        model = SupplierServiceRequest
        fields = [
            'id', 'supplier', 'supplier_id', 'service', 'service_id', 'unit_id',
            'request_type', 'quantity', 'special_requests', 'service_price',
            'delivery_fee', 'total_amount', 'status', 'requested_at', 'accepted_at',
            'completed_at', 'scheduled_date', 'scheduled_time', 'messages'
        ]
        read_only_fields = [
            'id', 'requested_at', 'accepted_at', 'completed_at', 'service_price',
            'delivery_fee', 'total_amount'
        ]

