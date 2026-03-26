from django.contrib import admin
from .models import Property, Unit, Lease, RentPayment, MaintenanceRequest

# Admin classes to manage the tenancy models in the Django admin interface
# This code defines how the Property, Unit, Lease, RentPayment, and MaintenanceRequest models are displayed and managed in the admin panel. It includes list displays, filters, search fields
class UnitInline(admin.TabularInline):
    model  = Unit
    extra  = 1
    fields = ['unit_number', 'bedrooms', 'bathrooms', 'is_occupied', 'is_available']




# Registering the models with the admin site and customizing their display and management options
# the owner field in the Property model is limited to users with the role of 'owner', so in the admin interface, when adding or editing a Property, only users who have the role of 'owner' will be available for selection in the owner dropdown. 
# This ensures that only authorized users can be assigned as property owners.
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display  = ['id', 'name', 'owner', 'property_type', 'city', 'lga', 'total_units', 'occupied_units']
    list_filter   = ['property_type', 'city', 'state', 'is_active']
    search_fields = ['name', 'address', 'owner__phone']
    inlines       = [UnitInline]



# unit admin interface includes filters for occupied and available units, and search fields for unit number and property name. This allows admin users to easily manage and find specific units within the properties.
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display  = ['id', 'unit_number', 'property', 'bedrooms', 'is_occupied', 'is_available']
    list_filter   = ['is_occupied', 'is_available']
    search_fields = ['unit_number', 'property__name']


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display  = ['id', 'tenant', 'unit', 'rent_frequency', 'rent_amount',
                     'total_lease_amount', 'start_date', 'end_date', 'status']
    list_filter   = ['status', 'rent_frequency']
    search_fields = ['tenant__phone', 'unit__property__name']

    # These methods are used to display related fields in the list display of the Lease admin interface.
    def get_unit(self, obj):
        return f"Unit {obj.unit.unit_number} (id:{obj.unit.id})"
    get_unit.short_description = 'Unit'

    def get_property(self, obj):
        return f"{obj.unit.property.name} (id:{obj.unit.property.id})"
    get_property.short_description = 'Property'


@admin.register(RentPayment)
class RentPaymentAdmin(admin.ModelAdmin):
    list_display  = ['id', 'reference', 'lease', 'amount', 'payment_method', 'status', 'paid_at']
    list_filter   = ['status', 'payment_method']
    search_fields = ['reference', 'lease__tenant__phone']



@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display  = ['id', 'title', 'unit', 'raised_by', 'category', 'urgency', 'status', 'is_overdue']
    list_filter   = ['status', 'category', 'urgency']
    search_fields = ['title', 'raised_by__phone']