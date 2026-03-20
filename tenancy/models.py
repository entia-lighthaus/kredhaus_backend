from django.db import models
from django.utils import timezone
from accounts.models import User


# ── Property ───────────────────────────────────────────────────────────────

class Property(models.Model):

    PROPERTY_TYPE_CHOICES = [
        ('flat',         'Flat / Apartment'),
        ('self_contain', 'Self Contained'),
        ('bq',           'Boys Quarters'),
        ('duplex',       'Duplex'),
        ('terrace',      'Terrace'),
        ('detached',     'Detached House'),
        ('commercial',   'Commercial'),
    ]


    owner         = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='properties',
        limit_choices_to={'role': 'owner'},
    )
    name          = models.CharField(max_length=128)
    property_type = models.CharField(max_length=30, choices=PROPERTY_TYPE_CHOICES)
    address       = models.CharField(max_length=255)
    city          = models.CharField(max_length=64)
    lga           = models.CharField(max_length=64)
    state         = models.CharField(max_length=64)
    description   = models.TextField(blank=True)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Properties'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.address}'

    @property
    def total_units(self):
        return self.units.count()

    @property
    def occupied_units(self):
        return self.units.filter(is_occupied=True).count()

    @property
    def vacant_units(self):
        return self.units.filter(is_occupied=False).count()



# ── Unit ───────────────────────────────────────────────────────────────────

class Unit(models.Model):

    property      = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='units',
    )
    unit_number   = models.CharField(max_length=20)   # e.g. "Flat 3", "Room B", "BQ"
    bedrooms      = models.PositiveSmallIntegerField(default=1)
    bathrooms     = models.PositiveSmallIntegerField(default=1)
    is_occupied   = models.BooleanField(default=False)
    is_available  = models.BooleanField(default=True)
    description   = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['property', 'unit_number']
        ordering = ['unit_number']

    def __str__(self):
        return f'{self.property.name} — {self.unit_number}'


# ── Lease ──────────────────────────────────────────────────────────────────
class Lease(models.Model):

    RENT_FREQUENCY_CHOICES = [
        ('3_months',  '3 Month Plan'),
        ('6_months',  'Bi-annual Plan'),
        ('9_months',  '9 Month Plan'),
        ('12_months', 'Annual Plan'),
    ]

    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('active',     'Active'),
        ('expired',    'Expired'),
        ('terminated', 'Terminated'),
    ]

    # Parties
    unit          = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='leases',
    )

    tenant        = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='leases',
        limit_choices_to={'role': 'tenant'},
    )

    # Terms
    rent_amount       = models.DecimalField(max_digits=12, decimal_places=2)
    rent_frequency    = models.CharField(
        max_length=20,
        choices=RENT_FREQUENCY_CHOICES,
        default='12_months',
    )
    
    total_lease_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False,
    )
    security_deposit  = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    # Dates
    start_date    = models.DateField()
    end_date      = models.DateField()
    status        = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )

    # Agreement
    agreed_by_tenant  = models.BooleanField(default=False)
    agreed_by_owner   = models.BooleanField(default=False)
    agreed_at         = models.DateTimeField(null=True, blank=True)

    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Lease: {self.tenant} @ {self.unit} ({self.status})'

    def save(self, *args, **kwargs):
        # Auto-calculate total lease amount
        multiplier = {
            '3_months':  3,
            '6_months':  6,
            '9_months':  9,
            '12_months': 12,
        }
        self.total_lease_amount = (
            self.rent_amount * multiplier.get(self.rent_frequency, 12)
        )
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        today = timezone.now().date()
        return (
            self.status == 'active' and
            self.start_date <= today <= self.end_date
        )

    @property
    def months_remaining(self):
        today = timezone.now().date()
        if today > self.end_date:
            return 0
        delta = self.end_date - today
        return round(delta.days / 30)


# ── Rent Payment ───────────────────────────────────────────────────────────

class RentPayment(models.Model):

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('card',          'Card'),
        ('ussd',          'USSD'),
        ('wallet',        'Wallet'),
    ]

    lease          = models.ForeignKey(
        Lease,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    amount         = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='bank_transfer',
    )
    status         = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    reference      = models.CharField(max_length=100, unique=True)
    paid_at        = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    note           = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Payment {self.reference} — ₦{self.amount} ({self.status})'





# ── Maintenance Request ────────────────────────────────────────────────────
class MaintenanceRequest(models.Model):

    CATEGORY_CHOICES = [
        ('plumbing',   'Plumbing'),
        ('electrical', 'Electrical'),
        ('structural', 'Structural'),
        ('appliance',  'Appliance'),
        ('cleaning',   'Cleaning'),
        ('security',   'Security'),
        ('other',      'Other'),
    ]

    STATUS_CHOICES = [
        ('open',        'Open'),
        ('assigned',    'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved',    'Resolved'),
        ('closed',      'Closed'),
    ]

    URGENCY_CHOICES = [
        ('urgent', 'Urgent — 24hr SLA'),
    ]

    unit        = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name='maintenance_requests',
    )

    raised_by   = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='maintenance_requests',
    )

    title       = models.CharField(max_length=128)
    description = models.TextField()
    category    = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    urgency     = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='urgent',
    )

    status      = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
    )


    # Resolution
    resolved_at   = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.urgency.upper()}] {self.title} — {self.unit}'

    @property
    def sla_hours(self):
        return 24

    @property
    def is_overdue(self):
        if self.status in ['resolved', 'closed']:
            return False
        from datetime import timedelta
        deadline = self.created_at + timedelta(hours=self.sla_hours)
        return timezone.now() > deadline