import uuid
from django.db import models
from django.utils import timezone
from accounts.models import User
from tenancy.models import Lease, Unit
from wallet.models import Wallet, Transaction


# ── Rent Advance ───────────────────────────────────────────────────────────
# Rent Advance is the flagship financing product — a short-term, fixed-fee loan to help tenants cover rent when they hit a cash flow crunch. 
# It’s designed to be simple, transparent, and affordable, with no compounding interest or hidden fees. Tenants choose how much they want to borrow (up to 6 months of rent) and how long they want to take to repay (3, 6 or 9 months). 
# The flat fee is calculated based on the amount and repayment period, so tenants know exactly how much they will owe from day one.
class RentAdvance(models.Model):

    PLAN_CHOICES = [
        ('3', '3 Months'),
        ('6', '6 Months'),
        ('9', '9 Months'),
    ]

    STATUS_CHOICES = [
        ('pending',   'Pending Approval'),
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('defaulted', 'Defaulted'),
        ('rejected',  'Rejected'),
    ]

    id               = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant           = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rent_advances',
    )
    lease            = models.ForeignKey(
        Lease,
        on_delete=models.CASCADE,
        related_name='advances',
    )
    wallet           = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='rent_advances',
    )

    # Financials
    # amount_requested is what tenant applies for; amount_approved is what they actually receive (which may be less if we have underwriting rules that limit the advance based on rent amount, repayment history, etc)
    amount_requested  = models.DecimalField(max_digits=12, decimal_places=2)
    amount_approved   = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    repayment_months  = models.CharField(
        max_length=2,
        choices=PLAN_CHOICES,
        default='6', 
    )
    flat_fee_percent  = models.DecimalField(max_digits=5, decimal_places=2)
    flat_fee_amount   = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    total_repayable   = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    monthly_repayment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    status            = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )

    # Reporting
    # We report to credit bureaus when the advance is approved, and again if repayments are missed or the advance defaults. 
    # This helps tenants build their credit history when they repay on time, and gives them an incentive to stay current.
    reported_to_bureau = models.BooleanField(default=False)
    disbursed_at       = models.DateTimeField(null=True, blank=True)
    completed_at       = models.DateTimeField(null=True, blank=True)
    rejection_reason   = models.TextField(blank=True)

    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'RentAdvance — {self.tenant.phone} — '
            f'₦{self.amount_approved} ({self.status})'
        )

    def calculate_financials(self):
        """
        Calculate fee, total repayable and
        monthly repayment based on plan.
        Called before saving.
        """
        from django.conf import settings
        fees = settings.RENT_ADVANCE_FEES
        fee_percent      = fees.get(str(self.repayment_months), 5.0)
        self.flat_fee_percent  = fee_percent
        self.flat_fee_amount   = (
            self.amount_requested * fee_percent / 100
        )
        self.total_repayable   = (
            self.amount_requested + self.flat_fee_amount
        )
        self.monthly_repayment = (
            self.total_repayable / int(self.repayment_months)
        )

    @property
    def amount_repaid(self):
        return sum(
            r.amount for r in self.repayments.filter(status='paid')
        )

    @property
    def amount_remaining(self):
        if not self.total_repayable:
            return 0
        return float(self.total_repayable) - float(self.amount_repaid)

    @property
    def payments_made(self):
        return self.repayments.filter(status='paid').count()

    @property
    def payments_total(self):
        return int(self.repayment_months)



# ── Rent Advance Repayment ─────────────────────────────────────────────────
# Each time a tenant makes a repayment towards their Rent Advance, we create a RentAdvanceRepayment record. 
# This allows us to track the repayment schedule, amounts, and status of each instalment. 
# It also helps with reporting to credit bureaus and calculating the tenant's credit score impact.
class RentAdvanceRepayment(models.Model):

    STATUS_CHOICES = [
        ('upcoming',  'Upcoming'),
        ('paid',      'Paid'),
        ('missed',    'Missed'),
        ('waived',    'Waived'),
    ]

    id              = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    advance         = models.ForeignKey(
        RentAdvance,
        on_delete=models.CASCADE,
        related_name='repayments',
    )
    amount          = models.DecimalField(max_digits=12, decimal_places=2)
    due_date        = models.DateField()
    paid_date       = models.DateTimeField(null=True, blank=True)
    status          = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='upcoming',
    )
    transaction     = models.ForeignKey(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    reported_to_bureau = models.BooleanField(default=False)
    instalment_number  = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['instalment_number']

    def __str__(self):
        return (
            f'Repayment {self.instalment_number} — '
            f'₦{self.amount} — {self.status}'
        )


# ── Utility Advance ────────────────────────────────────────────────────────
# Utility Advance is a similar product to Rent Advance but for utilities. 
# Tenants can apply for an advance to cover upcoming utility bills (electricity, water, gas, internet) and repay over time. 
# The financial structure is similar to Rent Advance, with a flat fee and fixed repayment schedule.
class UtilityAdvance(models.Model):

    UTILITY_TYPE_CHOICES = [
        ('electricity', 'Electricity'),
        ('gas',         'Gas'),
        ('water',       'Water'),
        ('internet',    'Internet'),
        ('other',       'Other'),
    ]

    PLAN_CHOICES = [
        ('1', '1 Month'),
        ('2', '2 Months'),
        ('3', '3 Months'),
    ]

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('defaulted', 'Defaulted'),
    ]

    id              = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant          = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='utility_advances',
    )
    wallet          = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='utility_advances',
    )
    utility_type    = models.CharField(
        max_length=20,
        choices=UTILITY_TYPE_CHOICES,
    )
    provider_name   = models.CharField(max_length=64)
    account_number  = models.CharField(max_length=50, blank=True)


    
    # Financials
    # amount_requested is what tenant applies for; amount_approved is what they actually receive (which may be less if we have underwriting rules that limit the advance based on repayment history, etc)
    amount_requested  = models.DecimalField(max_digits=10, decimal_places=2)
    flat_fee_percent  = models.DecimalField(max_digits=5, decimal_places=2)
    flat_fee_amount   = models.DecimalField(max_digits=10, decimal_places=2)
    total_repayable   = models.DecimalField(max_digits=10, decimal_places=2)
    repayment_months  = models.CharField(
        max_length=2,
        choices=PLAN_CHOICES,
        default='2',
    )
    monthly_repayment = models.DecimalField(max_digits=10, decimal_places=2)

    status            = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    disbursed_at      = models.DateTimeField(null=True, blank=True)
    completed_at      = models.DateTimeField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'UtilityAdvance — {self.tenant.phone} — '
            f'{self.utility_type} — ₦{self.amount_requested}'
        )

    def calculate_financials(self):
        from django.conf import settings
        fees = settings.UTILITY_ADVANCE_FEES
        fee_percent           = fees.get(str(self.repayment_months), 3.5)
        self.flat_fee_percent = fee_percent
        self.flat_fee_amount  = self.amount_requested * fee_percent / 100
        self.total_repayable  = self.amount_requested + self.flat_fee_amount
        self.monthly_repayment = (
            self.total_repayable / int(self.repayment_months)
        )



# We can create a similar UtilityAdvanceRepayment model to track repayments for utility advances, just like we do for rent advances.
# This keeps our data consistent and allows us to manage repayments in the same way across different financing products.
class UtilityAdvanceRepayment(models.Model):

    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('paid',     'Paid'),
        ('missed',   'Missed'),
    ]

    id              = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    advance         = models.ForeignKey(
        UtilityAdvance,
        on_delete=models.CASCADE,
        related_name='repayments',
    )
    amount          = models.DecimalField(max_digits=10, decimal_places=2)
    due_date        = models.DateField()
    paid_date       = models.DateTimeField(null=True, blank=True)
    status          = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='upcoming',
    )
    transaction     = models.ForeignKey(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    instalment_number = models.PositiveSmallIntegerField()
    reported_to_bureau = models.BooleanField(default=False)

    class Meta:
        ordering = ['instalment_number']

    def __str__(self):
        return (
            f'UtilityRepayment {self.instalment_number} — '
            f'₦{self.amount} — {self.status}'
        )




# ── Credit Builder Loan ────────────────────────────────────────────────────
# Credit Builder Loan is a longer-term loan product designed to help tenants build their credit history. 
# It works by locking the loan amount in a secure vault (a savings pocket in the wallet) while the tenant makes monthly repayments over 6 or 12 months. 
# As they repay on time, we report their positive payment history to credit bureaus, which can help improve their credit scores
# It alsod increase their chances of qualifying for larger loans in the future. The vault also earns a small amount of interest, which is paid out to the tenant when the loan is completed.
class CreditBuilderLoan(models.Model):

    PLAN_CHOICES = [
        ('6',  '6 Months'),
        ('12', '12 Months'),
    ]

    AMOUNT_CHOICES = [
        (50000,  '₦50,000'),
        (100000, '₦100,000'),
        (150000, '₦150,000'),
        (200000, '₦200,000'),
        (250000, '₦250,000'),
        (300000, '₦300,000'),
        (350000, '₦350,000'),
        (400000, '₦400,000'),
    ]

    STATUS_CHOICES = [
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('defaulted', 'Defaulted'),
    ]

    id              = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant          = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='credit_builder_loans',
    )
    wallet          = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='credit_builder_loans',
    )

    # The vault pocket where money is locked
    # This is a savings pocket that holds the loan amount while the tenant makes repayments. It earns interest over time, which is paid out to the tenant when the loan is completed. 
    # The vault also serves as collateral for the loan, giving us confidence to offer credit builder loans to tenants with limited credit history.
    vault_pocket    = models.OneToOneField(
        'wallet.SavingsPocket',
        on_delete=models.PROTECT,
        related_name='credit_builder_loan',
    )

    loan_amount     = models.DecimalField(max_digits=12, decimal_places=2)
    plan_months     = models.CharField(
        max_length=3,
        choices=PLAN_CHOICES,
        default='12',
    )
    monthly_fee     = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=1500.00,
    )
    monthly_principal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    monthly_total   = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    total_fees      = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    total_repayable = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    # Score tracking
    score_at_start  = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    score_current   = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    status          = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
    )
    started_at      = models.DateTimeField(auto_now_add=True)
    completed_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return (
            f'CreditBuilder — {self.tenant.phone} — '
            f'₦{self.loan_amount} — {self.plan_months}mo'
        )

    def calculate_financials(self):
        months                  = int(self.plan_months)
        self.monthly_principal  = self.loan_amount / months
        self.monthly_total      = self.monthly_principal + self.monthly_fee
        self.total_fees         = self.monthly_fee * months
        self.total_repayable    = self.loan_amount + self.total_fees

    @property
    def payments_made(self):
        return self.repayments.filter(status='paid').count()

    @property
    def payments_remaining(self):
        return int(self.plan_months) - self.payments_made

    @property
    def amount_repaid(self):
        return sum(
            r.monthly_total for r in self.repayments.filter(status='paid')
        )

    @property
    def interest_earned_on_vault(self):
        # Simple estimate: 8% p.a. on vault balance
        months = self.payments_made
        return round(
            float(self.loan_amount) * 0.08 * months / 12, 2
        )



# Each time a tenant makes a repayment towards their Credit Builder Loan, we create a CreditBuilderRepayment record. 
# This allows us to track the repayment schedule, amounts, and status of each instalment. 
# It also helps with reporting to credit bureaus and calculating the tenant's credit score impact.
class CreditBuilderRepayment(models.Model):

    STATUS_CHOICES = [
        ('upcoming',  'Upcoming'),
        ('paid',      'Paid'),
        ('missed',    'Missed'),
    ]

    id                 = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    loan               = models.ForeignKey(
        CreditBuilderLoan,
        on_delete=models.CASCADE,
        related_name='repayments',
    )
    instalment_number  = models.PositiveSmallIntegerField()
    principal_amount   = models.DecimalField(max_digits=12, decimal_places=2)
    fee_amount         = models.DecimalField(max_digits=8, decimal_places=2)
    monthly_total      = models.DecimalField(max_digits=12, decimal_places=2)
    due_date           = models.DateField()
    paid_date          = models.DateTimeField(null=True, blank=True)
    status             = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='upcoming',
    )
    transaction        = models.ForeignKey(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    reported_to_bureau = models.BooleanField(default=False) 
    # We report to credit bureaus when repayments are made, and also if repayments are missed. 
    # This helps tenants build their credit history when they repay on time, and gives them an incentive to stay current.
    # Our vision to create a financial identity for every tenant means that we want to ensure that all their positive financial behaviors 
    # are captured and reflected in their credit profile, while also encouraging responsible borrowing and repayment habits.
    bureau_reference   = models.CharField(max_length=128, blank=True) # This field can store the reference ID returned by the credit bureau when we report a repayment. It allows us to track which repayments have been reported and manage any updates or corrections if needed.

    class Meta:
        ordering = ['instalment_number']

    def __str__(self):
        return (
            f'CBRepayment {self.instalment_number} — '
            f'₦{self.monthly_total} — {self.status}'
        )