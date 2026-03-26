from django.db import models
from django.utils import timezone
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
