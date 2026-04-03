import uuid
from django.db import models
from django.utils import timezone
from accounts.models import User


# ── Wallet ─────────────────────────────────────────────────────────────────

class Wallet(models.Model):
    """
    Main wallet — one per user per currency.
    A Nigerian user has a NGN wallet.
    A diaspora landlord may also have a USD wallet.
    """

    CURRENCY_CHOICES = [
        ('NGN', 'Nigerian Naira'),
        ('USD', 'US Dollar'),
    ]

    id               = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user             = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wallets',
    )
    currency         = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='NGN',
    )
    balance          = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
    )
    ledger_balance   = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
        help_text='Balance including pending transactions',
    )


    # Flutterwave virtual account details
    virtual_account_number = models.CharField(
        max_length=20,
        blank=True,
    )
    virtual_bank_name      = models.CharField(
        max_length=64,
        blank=True,
    )
    flutterwave_ref        = models.CharField(
        max_length=128,
        blank=True,
    )

    is_active        = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'currency']
        ordering        = ['-created_at']

    def __str__(self):
        return f'{self.user.phone} — {self.currency} wallet'

    def can_debit(self, amount):
        """Check if wallet has sufficient balance."""
        return self.balance >= amount

    def credit(self, amount, description='', save=True):
        """Add funds to wallet."""
        self.balance        += amount
        self.ledger_balance += amount
        if save:
            self.save(update_fields=['balance', 'ledger_balance', 'updated_at'])

    def debit(self, amount, description='', save=True):
        """Remove funds from wallet."""
        if not self.can_debit(amount):
            raise ValueError(
                f'Insufficient balance. '
                f'Available: {self.balance}, Required: {amount}'
            )
        self.balance        -= amount
        self.ledger_balance -= amount
        if save:
            self.save(update_fields=['balance', 'ledger_balance', 'updated_at'])


# ── Savings Pocket ─────────────────────────────────────────────────────────

class SavingsPocket(models.Model):
    """
    Named savings pocket within a wallet.
    Money in a pocket is ring-fenced from
    the main balance — it cannot be spent
    without explicitly moving it back.
    """

    POCKET_TYPE_CHOICES = [
        ('rent',         'Next Rent'),
        ('home_deposit', 'Home Deposit'),
        ('emergency',    'Emergency Fund'),
        ('credit_vault', 'Credit Builder Vault'),
        ('utility',      'Utility Fund'),
        ('custom',       'Custom'),
    ] # Pre-defined pocket types for common use cases, but users can also create custom pockets with their own names.

    id           = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    wallet       = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='pockets',
    )
    pocket_type  = models.CharField(
        max_length=20,
        choices=POCKET_TYPE_CHOICES,
        default='custom',
    )
    name         = models.CharField(max_length=64)
    balance      = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
    )
    target_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Savings goal amount',
    )
    is_locked    = models.BooleanField(
        default=False,
        help_text='Locked pockets cannot be withdrawn from manually',
    )
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.wallet.user.phone} — {self.name}'

    @property
    def progress_percent(self):
        if not self.target_amount or self.target_amount == 0:
            return 0
        return min(
            round((float(self.balance) / float(self.target_amount)) * 100),
            100,
        )

    def credit(self, amount, save=True):
        self.balance += amount
        if save:
            self.save(update_fields=['balance'])

    def debit(self, amount, save=True):
        if self.is_locked:
            raise ValueError(
                'This pocket is locked and cannot be manually withdrawn.'
            )
        if self.balance < amount:
            raise ValueError('Insufficient pocket balance.')
        self.balance -= amount
        if save:
            self.save(update_fields=['balance'])


# ── Transaction ────────────────────────────────────────────────────────────

class Transaction(models.Model):
    """
    Immutable record of every money movement.
    Every credit, debit, transfer, fee, and
    advance is recorded here.
    """

    TYPE_CHOICES = [
        ('credit',          'Credit'),
        ('debit',           'Debit'),
        ('transfer_in',     'Transfer In'),
        ('transfer_out',    'Transfer Out'),
        ('rent_payment',    'Rent Payment'),
        ('utility_payment', 'Utility Payment'),
        ('advance_credit',  'Advance Disbursement'),
        ('advance_repay',   'Advance Repayment'),
        ('savings_deposit', 'Savings Deposit'),
        ('savings_withdraw','Savings Withdrawal'),
        ('fee',             'Platform Fee'),
        ('refund',          'Refund'),
    ]

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('reversed',  'Reversed'),
    ]

    id              = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    wallet          = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
    )
    amount          = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    currency        = models.CharField(max_length=3, default='NGN')
    balance_before  = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after   = models.DecimalField(max_digits=14, decimal_places=2)
    status          = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='completed',
    )
    reference       = models.CharField(max_length=128, unique=True)
    description     = models.TextField(blank=True)

    # External payment reference (Flutterwave)
    provider_ref    = models.CharField(max_length=128, blank=True)
    provider        = models.CharField(max_length=50, blank=True)

    # Related objects (optional links)
    related_pocket  = models.ForeignKey(
        SavingsPocket,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    created_at      = models.DateTimeField(auto_now_add=True)
    metadata        = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'{self.transaction_type} — '
            f'{self.currency} {self.amount} — '
            f'{self.reference}'
        )


# ── Virtual Account ────────────────────────────────────────────────────────
class VirtualAccount(models.Model):
    """
    Flutterwave virtual account number assigned
    to each wallet. Tenants fund their wallet by
    bank transfer to this account number.
    """

    wallet          = models.OneToOneField(
        Wallet,
        on_delete=models.CASCADE,
        related_name='virtual_account',
    )
    account_number  = models.CharField(max_length=20)
    bank_name       = models.CharField(max_length=64)
    account_name    = models.CharField(max_length=128)
    flutterwave_ref = models.CharField(max_length=128)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f'{self.account_number} — '
            f'{self.bank_name} — '
            f'{self.wallet.user.phone}'
        )