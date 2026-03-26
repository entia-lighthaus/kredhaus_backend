from django.db import models
from django.utils import timezone
from datetime import timedelta
from tenancy.models import Unit


# ── Utility ────────────────────────────────────────────────────────────────

class Utility(models.Model):
    """
    Represents a utility type (Electricity, Gas, Water, Internet).
    These are master records maintained by admins.
    """

    TYPE_CHOICES = [
        ('electricity', 'Electricity'),
        ('gas',         'Gas'),
        ('water',       'Water'),
        ('internet',    'Internet'),
    ]

    name            = models.CharField(max_length=50, choices=TYPE_CHOICES, unique=True)
    display_name    = models.CharField(max_length=100)  # e.g., "EEDC Power"
    icon_color      = models.CharField(max_length=7, default='#000000')  # Hex color for UI
    description     = models.TextField(blank=True)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Utilities'
        ordering = ['name']

    def __str__(self):
        return self.display_name


# ── Utility Account ───────────────────────────────────────────────────────

class UtilityAccount(models.Model):
    """
    Represents a tenant's utility account for a specific unit with balance tracking, bill due dates, and status.
    E.g., Electricity account for Apartment 3A.
    """

    STATUS_CHOICES = [
        ('active',     'Active'),
        ('pending',    'Pending'),
        ('inactive',   'Inactive'),
        ('suspended',  'Suspended'),
    ]

    unit            = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='utility_accounts'
    )
    utility         = models.ForeignKey(
        Utility,
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    
    # Account Details
    account_number  = models.CharField(max_length=100)
    account_name    = models.CharField(max_length=255, blank=True)
    provider        = models.CharField(max_length=128, blank=True)  # e.g., "Lagos State"
    
    # Account Status
    status          = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    # Financial Info
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    last_bill_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    bill_due_date   = models.DateField(null=True, blank=True)
    
    # Metadata
    connected_by    = models.CharField(max_length=255, blank=True)  # Name of tenant who connected
    connected_at    = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    last_updated_by = models.CharField(max_length=255, blank=True)  # Who last updated

    class Meta:
        unique_together = ['unit', 'utility']
        ordering = ['-connected_at']

    def __str__(self):
        return f'{self.utility.display_name} — {self.account_number}'

    @property
    def is_overdue(self):
        """Check if bill is overdue."""
        if not self.bill_due_date:
            return False
        return timezone.now().date() > self.bill_due_date

    @property
    def days_until_due(self):
        """Days until bill is due."""
        if not self.bill_due_date:
            return None
        delta = self.bill_due_date - timezone.now().date()
        return max(0, delta.days)



# ── Utility Bill ───────────────────────────────────────────────────────────

class UtilityBill(models.Model):
    """
    Individual bill records for utility accounts (with payment status and overdue detection).
    Helps track billing history.
    """

    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('due',        'Due'),
        ('overdue',    'Overdue'),
        ('paid',       'Paid'),
    ]

    account         = models.ForeignKey(
        UtilityAccount,
        on_delete=models.CASCADE,
        related_name='bills'
    )
    
    # Bill Details
    bill_reference  = models.CharField(max_length=100, unique=True)
    amount          = models.DecimalField(max_digits=12, decimal_places=2)
    status          = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Dates
    bill_date       = models.DateField()  # When bill was issued
    due_date        = models.DateField()  # When payment is due
    paid_date       = models.DateField(null=True, blank=True)  # When paid
    
    # Notes
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-bill_date']

    def __str__(self):
        return f'{self.account.utility.display_name} Bill — {self.bill_reference}'

    @property
    def is_overdue(self):
        if self.status == 'paid':
            return False
        return timezone.now().date() > self.due_date


# ── Utility Rate ────────────────────────────────────────────────────────────

class UtilityRate(models.Model):
    """
    Pricing configuration for utilities.
    Supports tariff bands, fixed charges, and effective date ranges.
    """

    UNIT_CHOICES = [
        ('kwh',     'Kilowatt Hours'),
        ('liters',  'Litres'),
        ('mbps',    'Megabits per Second'),
        ('units',   'Units'),
    ]

    BAND_CHOICES = [
        ('A', 'Band A'),
        ('B', 'Band B'),
        ('C', 'Band C'),
        ('D', 'Band D'),
        ('E', 'Band E'),
    ]

    utility         = models.ForeignKey(
        Utility,
        on_delete=models.CASCADE,
        related_name='rates'
    )
    band            = models.CharField(max_length=20, choices=BAND_CHOICES, default='C')

    # Pricing
    unit            = models.CharField(max_length=20, choices=UNIT_CHOICES)
    rate            = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Cost per unit (e.g., ₦50 per kWh)"
    )
    fixed_charge    = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Fixed charge for this band"
    )
    min_consumption = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Lowest consumption value for wage band (optional)"
    )
    max_consumption = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Highest consumption value for wage band (optional)"
    )
    
    # Validity
    effective_from  = models.DateField()
    effective_to    = models.DateField(null=True, blank=True)
    is_active       = models.BooleanField(default=True)
    
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Utility Rates'
        ordering = ['utility', 'band', '-effective_from']
        unique_together = ['utility', 'band', 'effective_from']

    def __str__(self):
        return f'{self.utility.display_name} - Band {self.band} ({self.unit}) @ ₦{self.rate}'

    @property
    def is_current(self):
        today = timezone.now().date()
        return (
            self.is_active and
            self.effective_from <= today and
            (self.effective_to is None or today <= self.effective_to)
        )

    def contains_consumption(self, consumption):
        if self.min_consumption is not None and consumption < self.min_consumption:
            return False
        if self.max_consumption is not None and consumption > self.max_consumption:
            return False
        return True


# ── Meter Provider Configuration ─────────────────────────────────────────────

class UtilityMeterProvider(models.Model):
    """
    Configures HOW consumption data is captured for a utility account.
    Supports smart meters (API push), manual input, or hybrid.
    """
    
    METHOD_CHOICES = [
        ('smart_meter',    'Smart Meter (Auto Push)'),
        ('manual_reading', 'Manual Meter Reading'),
        ('hybrid',         'Hybrid (Smart + Manual Override)'),
    ]
    
    READING_TYPE_CHOICES = [
        ('consumption',      'Direct Consumption (kWh, L)'),
        ('meter_difference', 'Previous vs Current Reading'),
    ]

    account         = models.OneToOneField(
        UtilityAccount,
        on_delete=models.CASCADE,
        related_name='meter_provider'
    )
    
    # Data Source Configuration
    method          = models.CharField(max_length=50, choices=METHOD_CHOICES)
    reading_type    = models.CharField(
        max_length=50,
        choices=READING_TYPE_CHOICES,
        default='meter_difference'
    )
    tariff_band     = models.CharField(
        max_length=20,
        choices=UtilityRate.BAND_CHOICES,
        null=True,
        blank=True,
        help_text='Tariff band (A-E) selected for this account'
    )
    
    # For smart meters
    provider_name   = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g., EEDC, Lagos Water, etc."
    )
    api_key         = models.CharField(
        max_length=500,
        blank=True,
        help_text="API key for smart meter provider (should be encrypted)"
    )
    webhook_token   = models.CharField(
        max_length=255,
        blank=True,
        help_text="Token to validate webhook requests"
    )
    
    # For manual input
    manual_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily',     'Daily'),
            ('weekly',    'Weekly'),
            ('monthly',   'Monthly'),
        ],
        default='monthly'
    )
    
    # Status & Tracking
    is_active       = models.BooleanField(default=True)
    last_reading_date = models.DateField(null=True, blank=True)
    last_sync_attempt = models.DateTimeField(null=True, blank=True)
    
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Meter Provider'

    def __str__(self):
        return f'{self.account} ({self.get_method_display()})'


# ── Meter Reading (Raw Data) ────────────────────────────────────────────────

class UtilityMeterReading(models.Model):
    """
    Raw meter data captured from ANY source (smart meter push or manual input).
    
    Examples:
    - Smart meter: previous_reading=100, current_reading=145
    - Manual input: previous_reading=100, current_reading=145
    - Direct consumption: consumption=45 (no readings needed)
    """
    
    SOURCE_CHOICES = [
        ('smart_meter', 'Smart Meter (API Push)'),
        ('manual',      'Manual Tenant Input'),
        ('import',      'Bulk Import'),
    ]

    account         = models.ForeignKey(
        UtilityAccount,
        on_delete=models.CASCADE,
        related_name='meter_readings'
    )
    
    # OPTION 1: Meter Readings (difference method)
    previous_reading = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Reading from last period"
    )
    current_reading = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Reading for this period"
    )
    
    # OPTION 2: Direct Consumption
    # This is for cases where we get actual consumption data directly (e.g., from smart meter API) without needing to calculate difference.
    consumption     = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Direct consumption (kWh, litres, etc)"
    )
    
    # Metadata
    reading_date    = models.DateField()
    source          = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    tariff_band     = models.CharField(
        max_length=20,
        choices=UtilityRate.BAND_CHOICES,
        null=True,
        blank=True,
        help_text='Optional selected tariff band for this reading'
    )
    
    # Status
    is_processed    = models.BooleanField(default=False)
    is_confirmed    = models.BooleanField(default=False)
    
    # Audit
    submitted_by    = models.CharField(
        max_length=255,
        blank=True,
        help_text="Tenant name or API system"
    )
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reading_date']
        unique_together = ['account', 'reading_date']

    def __str__(self):
        if self.consumption:
            return f'{self.account} — {self.consumption} units on {self.reading_date}'
        else:
            diff = self.calculated_consumption if self.calculated_consumption else 0
            return f'{self.account} — {diff} units on {self.reading_date}'
    
    @property
    def calculated_consumption(self):
        """Calculate actual consumption based on reading type."""
        if self.consumption is not None:
            return self.consumption
        if self.current_reading is not None and self.previous_reading is not None:
            return self.current_reading - self.previous_reading
        return 0


# ── Processed Usage Record ──────────────────────────────────────────────────

class UtilityUsageRecord(models.Model):
    """
    Processed consumption record derived from meter reading.
    One-to-one relationship with MeterReading (data integrity).
    This is what gets billed.
    """
    
    meter_reading   = models.OneToOneField(
        UtilityMeterReading,
        on_delete=models.CASCADE,
        related_name='usage_record'
    )
    
    account         = models.ForeignKey(
        UtilityAccount,
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    
    # Processed Data
    consumption     = models.DecimalField(max_digits=10, decimal_places=2)
    unit            = models.CharField(
        max_length=20,
        choices=[
            ('kwh',     'Kilowatt Hours'),
            ('liters',  'Litres'),
            ('mbps',    'Megabits per Second'),
            ('units',   'Units'),
        ]
    )
    
    # Billing Period
    period_start    = models.DateField()
    period_end      = models.DateField()
    
    # Cost Breakdown
    unit_rate       = models.DecimalField(max_digits=10, decimal_places=4)
    variable_cost   = models.DecimalField(max_digits=12, decimal_places=2)  # consumption * rate
    fixed_charge    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_due      = models.DecimalField(max_digits=12, decimal_places=2)  # total to pay
    
    # Status
    is_billed       = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-period_end']

    def __str__(self):
        return f'{self.account} — {self.consumption}{self.unit} (₦{self.amount_due})'

    @property
    def cost_breakdown(self):
        """Return detailed cost breakdown."""
        return {
            'consumption': float(self.consumption),
            'unit': self.unit,
            'unit_rate': float(self.unit_rate),
            'variable_cost': float(self.variable_cost),
            'fixed_charge': float(self.fixed_charge),
            'total_amount_due': float(self.amount_due),
        }


# ── Supplier Management (Gas, Water, etc) ──────────────────────────────────

class Supplier(models.Model):
    """
    Gas/Water supplier company profile.
    Vendors who offer refill services.
    """
    
    STATUS_CHOICES = [
        ('active',      'Active'),
        ('inactive',    'Inactive'),
        ('suspended',   'Suspended'),
    ]

    utility         = models.ForeignKey(
        Utility,
        on_delete=models.CASCADE,
        related_name='suppliers',
        help_text='Gas, Water, etc.'
    )
    
    # Company Info
    company_name    = models.CharField(max_length=255)
    description     = models.TextField(blank=True)
    logo            = models.ImageField(upload_to='supplier_logos/', null=True, blank=True)
    icon_color      = models.CharField(max_length=7, default='#FF4500')  # Hex color for UI
    
    # Contact
    phone_number    = models.CharField(max_length=20)
    email           = models.EmailField(blank=True)
    address         = models.CharField(max_length=255, blank=True)
    city            = models.CharField(max_length=100, blank=True)
    
    # Ratings & Reviews
    average_rating  = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        default=5.0,
        help_text='Average rating from 1-5 stars'
    )
    total_reviews   = models.IntegerField(default=0)
    
    # Availability
    status          = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    is_available    = models.BooleanField(default=True)
    pickup_time_minutes = models.IntegerField(default=30, help_text='Average pickup time in minutes')
    delivery_fee    = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000,
        help_text='Delivery charge in Naira'
    )
    
    # Compliance
    is_safety_certified = models.BooleanField(default=True)
    
    # Metadata
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-average_rating', 'company_name']
        unique_together = ['utility', 'phone_number']

    def __str__(self):
        return f'{self.company_name} ({self.utility.display_name})'


class SupplierService(models.Model):
    """
    What a supplier offers (12kg gas cylinder, 6kg gas cylinder, delivery, etc).
    """
    
    supplier        = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='services'
    )
    
    # Service Details
    name            = models.CharField(max_length=255)  # e.g., "12kg Gas Cylinder Refill"
    description     = models.TextField(blank=True)
    price           = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Specifications
    quantity        = models.CharField(
        max_length=100,
        blank=True,
        help_text='e.g., "12kg", "1 cylinder", "500L"'
    )
    
    # Status
    is_available    = models.BooleanField(default=True)
    
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.supplier.company_name} - {self.name}'


class SupplierAvailability(models.Model):
    """
    Real-time availability status of suppliers.
    """
    
    supplier        = models.OneToOneField(
        Supplier,
        on_delete=models.CASCADE,
        related_name='availability'
    )
    
    # Status
    is_online       = models.BooleanField(default=True)
    current_orders  = models.IntegerField(default=0, help_text='Number of active orders')
    max_daily_orders = models.IntegerField(default=50)
    
    # Tracking
    last_updated    = models.DateTimeField(auto_now=True)
    last_order_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Supplier Availabilities'

    def __str__(self):
        status = 'Online' if self.is_online else 'Offline'
        return f'{self.supplier.company_name} - {status}'


class SupplierServiceRequest(models.Model):
    """
    Tenant's order request to a supplier (pickup/delivery request).
    """
    
    STATUS_CHOICES = [
        ('pending',     'Pending'),
        ('accepted',    'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed',   'Completed'),
        ('cancelled',   'Cancelled'),
    ]

    # Relationships
    supplier        = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='service_requests'
    )
    
    service         = models.ForeignKey(
        SupplierService,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requests'
    )
    
    unit            = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='supplier_requests'
    )
    
    # Request Details
    request_type    = models.CharField(
        max_length=20,
        choices=[
            ('pickup',    'Pickup'),
            ('delivery',  'Delivery'),
        ],
        default='pickup'
    )
    
    quantity        = models.IntegerField(default=1, help_text='Number of cylinders/units')
    special_requests = models.TextField(blank=True, help_text='Any special instructions')
    
    # Pricing
    service_price   = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    status          = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Timestamps
    requested_at    = models.DateTimeField(auto_now_add=True)
    accepted_at     = models.DateTimeField(null=True, blank=True)
    completed_at    = models.DateTimeField(null=True, blank=True)
    scheduled_date  = models.DateField(null=True, blank=True)
    scheduled_time  = models.TimeField(null=True, blank=True)
    
    # Tracking
    created_by      = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.unit} - {self.supplier.company_name} (#{self.id})'


class SupplierMessage(models.Model):
    """
    Chat messages between tenant and supplier for a service request.
    """
    
    service_request = models.ForeignKey(
        SupplierServiceRequest,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # Message Details
    sender_type     = models.CharField(
        max_length=20,
        choices=[
            ('tenant',   'Tenant'),
            ('supplier', 'Supplier'),
        ]
    )
    
    sender_name     = models.CharField(max_length=255)
    message_text    = models.TextField()
    
    # Attachments (optional)
    attachment_url  = models.URLField(blank=True, null=True, help_text='Image or file URL')
    
    # Status
    is_read         = models.BooleanField(default=False)
    
    # Timestamp
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender_name} -> {self.service_request.supplier.company_name}'


class SupplierRating(models.Model):
    """
    Tenant's rating and review for a supplier after service completion.
    """
    
    supplier        = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    
    service_request = models.OneToOneField(
        SupplierServiceRequest,
        on_delete=models.CASCADE,
        related_name='rating'
    )
    
    unit            = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='supplier_ratings'
    )
    
    # Rating Details
    rating          = models.IntegerField(
        choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)]
    )
    review_text     = models.TextField(blank=True)
    
    # Categories (optional)
    cleanliness     = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)]
    )
    professionalism = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)]
    )
    timeliness      = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)]
    )
    
    # Reviewer Info
    reviewer_name   = models.CharField(max_length=255, blank=True)
    
    # Timestamp
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['supplier', 'service_request']

    def __str__(self):
        return f'{self.supplier.company_name} - {self.rating}★ by {self.reviewer_name}'

