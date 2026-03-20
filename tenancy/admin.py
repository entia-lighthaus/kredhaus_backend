from django.contrib import admin
from .models import Property, Unit, Lease, RentPayment, MaintenanceRequest


class UnitInline(admin.TabularInline):
    model  = Unit
    extra  = 1
    fields = ['unit_number', 'bedrooms', 'bathrooms', 'is_occupied', 'is_available']


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display  = ['name', 'owner', 'property_type', 'city', 'lga', 'total_units', 'occupied_units']
    list_filter   = ['property_type', 'state', 'is_active']
    search_fields = ['name', 'address', 'owner__phone']
    inlines       = [UnitInline]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display  = ['unit_number', 'property', 'bedrooms', 'is_occupied', 'is_available']
    list_filter   = ['is_occupied', 'is_available']
    search_fields = ['unit_number', 'property__name']


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display  = ['tenant', 'unit', 'rent_frequency', 'rent_amount',
                     'total_lease_amount', 'start_date', 'end_date', 'status']
    list_filter   = ['status', 'rent_frequency']
    search_fields = ['tenant__phone', 'unit__property__name']


@admin.register(RentPayment)
class RentPaymentAdmin(admin.ModelAdmin):
    list_display  = ['reference', 'lease', 'amount', 'payment_method', 'status', 'paid_at']
    list_filter   = ['status', 'payment_method']
    search_fields = ['reference', 'lease__tenant__phone']


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display  = ['title', 'unit', 'raised_by', 'category', 'urgency', 'status', 'is_overdue']
    list_filter   = ['status', 'category', 'urgency']
    search_fields = ['title', 'raised_by__phone']