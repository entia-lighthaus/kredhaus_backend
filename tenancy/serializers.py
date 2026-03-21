from rest_framework import serializers
from .models import Property, Unit, Lease, RentPayment, MaintenanceRequest
from accounts.models import User
import uuid


# ── Property Serializers ───────────────────────────────────────────────────
# It is used by the owner to create and view their properties. It includes computed fields for total units, occupied units, and vacant units, which are derived from the related Unit records. 
# The owner_name field is a read-only field that concatenates the first and last name of the property owner for display purposes.
class PropertySerializer(serializers.ModelSerializer):
    
    total_units    = serializers.ReadOnlyField()
    occupied_units = serializers.ReadOnlyField()
    vacant_units   = serializers.ReadOnlyField()
    owner_name     = serializers.SerializerMethodField()

    class Meta:
        model  = Property
        fields = [
            'id',
            'owner_name',
            'name',
            'property_type',
            'address',
            'city',
            'lga',
            'state',
            'description',
            'is_active',
            'total_units',
            'occupied_units',
            'vacant_units',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_owner_name(self, obj):
        return f'{obj.owner.first_name} {obj.owner.last_name}'



# ── Unit Serializers ───────────────────────────────────────────────────────
# The UnitSerializer is used by the property owner to add and manage units within a property. 
# It includes a read-only field for the property name, which is derived from the related Property record. 
# The UnitTenantSerializer is a simplified view of the unit that is intended for tenants, showing only relevant details without exposing financial or ownership information.
class UnitSerializer(serializers.ModelSerializer):
    
    property_name = serializers.CharField(
        source='property.name',
        read_only=True,
    )

    class Meta:
        model  = Unit
        fields = [
            'id',
            'property',
            'property_name',
            'unit_number',
            'image',
            'bedrooms',
            'bathrooms',
            'is_occupied',
            'is_available',
            'description',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'is_occupied', 'property']



# The UnitTenantSerializer is a simplified view of the unit that is intended for tenants, showing only relevant details without exposing financial or ownership information.
# It includes the property name and address for context, but omits fields like occupancy status and availability, which are not relevant to the tenant's view of their own unit.
class UnitTenantSerializer(serializers.ModelSerializer):
   
    property_name    = serializers.CharField(
        source='property.name',
        read_only=True,
    )

    property_address = serializers.CharField(
        source='property.address',
        read_only=True,
    )

    class Meta:
        model  = Unit
        fields = [
            'id',
            'unit_number',
            'image',
            'property_name',
            'property_address',
            'bedrooms',
            'bathrooms',
            'description',
        ]




# ── Lease Serializers ──────────────────────────────────────────────────────
# The LeaseOwnerSerializer provides a comprehensive view of a lease for the property owner, including tenant details, total payments made, and the status of the lease.
class LeaseOwnerSerializer(serializers.ModelSerializer):
    
    tenant_name     = serializers.SerializerMethodField()
    tenant_phone    = serializers.SerializerMethodField()
    unit_number     = serializers.CharField(
        source='unit.unit_number',
        read_only=True,
    )
    property_name   = serializers.CharField(
        source='unit.property.name',
        read_only=True,
    )
    total_paid      = serializers.SerializerMethodField()
    months_remaining = serializers.ReadOnlyField()
    is_active       = serializers.ReadOnlyField()

    class Meta:
        model  = Lease
        fields = [
            'id',
            'unit',
            'unit_number',
            'property_name',
            'tenant',
            'tenant_name',
            'tenant_phone',
            'rent_amount',
            'rent_frequency',
            'total_lease_amount',
            'security_deposit',
            'start_date',
            'end_date',
            'status',
            'agreed_by_tenant',
            'agreed_by_owner',
            'agreed_at',
            'total_paid',
            'months_remaining',
            'is_active',
            'created_at',
        ]

        # Define read-only fields to prevent modification of certain fields through the API. 
        # This ensures data integrity and that certain fields are only set by the system or through specific actions (like agreement timestamps).
        read_only_fields = [
            'id',
            'total_lease_amount',
            'agreed_at',
            'created_at',
        ]

    def get_tenant_name(self, obj):
        return f'{obj.tenant.first_name} {obj.tenant.last_name}'

    def get_tenant_phone(self, obj):
        return obj.tenant.phone

    def get_total_paid(self, obj):
        completed = obj.payments.filter(status='completed')
        return sum(p.amount for p in completed)



class LeaseTenantSerializer(serializers.ModelSerializer):
    """
    Tenant's view of their own lease.
    Shows their terms and obligations only.
    Does not expose other tenants or
    owner financial details.
    """
    unit_details     = UnitTenantSerializer(source='unit', read_only=True)
    months_remaining = serializers.ReadOnlyField()
    is_active        = serializers.ReadOnlyField()
    total_paid       = serializers.SerializerMethodField()
    balance_due      = serializers.SerializerMethodField()

    class Meta:
        model  = Lease
        fields = [
            'id',
            'unit_details',
            'rent_amount',
            'rent_frequency',
            'total_lease_amount',
            'security_deposit',
            'start_date',
            'end_date',
            'status',
            'agreed_by_tenant',
            'months_remaining',
            'is_active',
            'total_paid',
            'balance_due',
            'created_at',
        ]
        read_only_fields = fields

    def get_total_paid(self, obj):
        completed = obj.payments.filter(status='completed')
        return sum(p.amount for p in completed)

    def get_balance_due(self, obj):
        return float(obj.total_lease_amount) - float(
            self.get_total_paid(obj)
        )


# The LeaseCreateSerializer is used by the owner to create a new lease. It looks up the tenant by their phone number, ensuring that the tenant exists and is valid before creating the lease. 
# It also includes validation to prevent creating a lease on an occupied unit and to ensure that the end date is after the start date.
class LeaseCreateSerializer(serializers.ModelSerializer):
    """
    Tenant's view of their own lease.
    """
    tenant_phone = serializers.CharField(write_only=True)

    class Meta:
        model  = Lease
        fields = [
            'unit',
            'tenant_phone',
            'rent_amount',
            'rent_frequency',
            'security_deposit',
            'start_date',
            'end_date',
        ]

    def validate_tenant_phone(self, value):
        if value.startswith('0'):
            value = '+234' + value[1:]
        try:
            user = User.objects.get(phone=value, role='tenant')
        except User.DoesNotExist:
            raise serializers.ValidationError(
                'No tenant account found with this phone number.'
            )
        return value

    def validate(self, attrs):
        unit = attrs.get('unit')

        # Block creating a lease on an occupied unit
        if unit and unit.is_occupied:
            raise serializers.ValidationError(
                {'unit': 'This unit is already occupied.'}
            )

        # Block end date before start date
        if attrs['start_date'] >= attrs['end_date']:
            raise serializers.ValidationError(
                {'end_date': 'End date must be after start date.'}
            )

        return attrs

    def create(self, validated_data):
        tenant_phone = validated_data.pop('tenant_phone')

        if tenant_phone.startswith('0'):
            tenant_phone = '+234' + tenant_phone[1:]

        tenant = User.objects.get(phone=tenant_phone)
        lease  = Lease.objects.create(
            tenant=tenant,
            **validated_data,
        )
        return lease



# ── Rent Payment Serializers ───────────────────────────────────────────────
# The RentPaymentSerializer is a read-only serializer that both owners and tenants can use to view payment records. 
# It includes a method to get the tenant's name for display purposes. 
class RentPaymentSerializer(serializers.ModelSerializer):
    
    tenant_name = serializers.SerializerMethodField()

    class Meta:
        model  = RentPayment
        fields = [
            'id',
            'lease',
            'tenant_name',
            'amount',
            'payment_method',
            'status',
            'reference',
            'paid_at',
            'note',
            'created_at',
        ]
        read_only_fields = fields

    def get_tenant_name(self, obj):
        return f'{obj.lease.tenant.first_name} {obj.lease.tenant.last_name}'



# The RentPaymentCreateSerializer is used by tenants to initiate a payment, with validation to ensure they can only pay against their own active or pending leases and that the payment amount is valid. 
# It also auto-generates a unique payment reference upon creation.
class RentPaymentCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = RentPayment
        fields = [
            'lease',
            'amount',
            'payment_method',
            'note',
        ]

    def validate_lease(self, value):
        request = self.context['request']

        # Tenant can only pay against their own lease
        if value.tenant != request.user:
            raise serializers.ValidationError(
                'You can only make payments against your own lease.'
            )

        # Block payment on inactive lease
        if value.status not in ['active', 'pending']:
            raise serializers.ValidationError(
                'Payments can only be made on active or pending leases.'
            )

        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Payment amount must be greater than zero.'
            )
        return value

    def create(self, validated_data):
        # Auto-generate a unique payment reference
        reference = 'KH-' + str(uuid.uuid4()).upper()[:12]
        payment   = RentPayment.objects.create(
            reference=reference,
            status='completed',
            **validated_data,
        )
        return payment




# ── Maintenance Request Serializers ───────────────────────────────────────
# The MaintenanceRequestSerializer is a read serializer that both owners and tenants can use to view maintenance requests. 
# It includes fields for the unit number, property name, and the name of the person who raised the request, as well as a computed field to indicate if the request is overdue.
class MaintenanceRequestSerializer(serializers.ModelSerializer):
    
    raised_by_name = serializers.SerializerMethodField()
    unit_number    = serializers.CharField(
        source='unit.unit_number',
        read_only=True,
    )
    property_name  = serializers.CharField(
        source='unit.property.name',
        read_only=True,
    )
    is_overdue     = serializers.ReadOnlyField()

    class Meta:
        model  = MaintenanceRequest
        fields = [
            'id',
            'unit',
            'unit_number',
            'property_name',
            'raised_by',
            'raised_by_name',
            'title',
            'description',
            'photo',
            'category',
            'urgency',
            'status',
            'is_overdue',
            'resolved_at',
            'resolution_note',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'raised_by',
            'status',
            'resolved_at',
            'created_at',
            'updated_at',
        ]

    def get_raised_by_name(self, obj):
        return f'{obj.raised_by.first_name} {obj.raised_by.last_name}'


# The MaintenanceRequestCreateSerializer is used by tenants to raise a new maintenance request. It includes validation to ensure that tenants can only raise requests for units they are currently renting, based on their active leases.
class MaintenanceRequestCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model  = MaintenanceRequest
        fields = [
            'unit',
            'title',
            'description',
            'photo',
            'category',
            'urgency',
        ]

    def validate_unit(self, value):
        request = self.context['request']

        # Confirm tenant has an active lease on this unit
        has_lease = Lease.objects.filter(
            unit=value,
            tenant=request.user,
            status='active',
        ).exists()

        if not has_lease:
            raise serializers.ValidationError(
                'You can only raise requests for units you are '
                'currently renting.'
            )
        return value


# The MaintenanceStatusUpdateSerializer is used by the property owner to update the status of a maintenance request. 
# It includes validation to ensure that only valid status values can be set and automatically records the resolution time when a request is marked as resolved.
class MaintenanceStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Used by Owner to update the status of a request.
    """

    class Meta:
        model  = MaintenanceRequest
        fields = [
            'status',
            'resolution_note',
        ]

    def validate_status(self, value):
        valid = ['assigned', 'in_progress', 'resolved', 'closed']
        if value not in valid:
            raise serializers.ValidationError(
                f'Status must be one of: {", ".join(valid)}'
            )
        return value

    def update(self, instance, validated_data):
        if validated_data.get('status') == 'resolved':
            from django.utils import timezone
            instance.resolved_at = timezone.now()
        instance.status          = validated_data.get('status', instance.status)
        instance.resolution_note = validated_data.get('resolution_note', instance.resolution_note)
        instance.save()
        return instance