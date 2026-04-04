import uuid
from django.db import models
from django.utils import timezone
from accounts.models import User


# ── Wallet ─────────────────────────────────────────────────────────────────
# wallet is infrastructure — it is the plumbing every other feature depends on. Payments, balances, transactions, and savings all live here. It needs to exist before financing can work because Rent Advance disbursements and repayments flow through the wallet.
# financing is products — it sits on top of the wallet. A Rent Advance reads the wallet balance, disburses through the wallet, and collects repayments from the wallet.
# Building wallet first means financing works correctly from day one instead of having circular dependencies.
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

    # Ledger balance includes pending transactions that haven't settled yet. This is what the user sees as their "available balance" in the app, while the `balance` field reflects only completed transactions. 
    # For example, if a user has a balance of 1000 NGN and initiates a payment of 200 NGN, the `balance` remains 1000 until the transaction completes, but the `ledger_balance` immediately reflects 800 NGN to show the pending deduction.
    ledger_balance   = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0.00,
        help_text='Balance including pending transactions',
    )


    # Flutterwave virtual account details
    # These fields are populated when a virtual account is created for the wallet. 
    # They allow tenants to fund their wallet by transferring money to the assigned virtual account number. The webhook listens for incoming payments to this account and credits the wallet accordingly.
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


    # The `unique_together` constraint ensures that a user cannot have multiple wallets with the same currency, enforcing a one-wallet-per-currency rule. 
    # This simplifies balance management and transaction processing, as each user has a single source of truth for their funds in each currency.
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
# pockets are sub-wallets for specific savings goals. They help users set aside money for rent, deposits, emergencies, or any custom purpose.
# Pockets can be locked to prevent manual withdrawals, ensuring funds are reserved for their intended use. For example, a "Rent" pocket would be locked to ensure that money saved for rent isn't accidentally spent on something else. 
# The system can only debit from locked pockets when a payment is due, which promotes disciplined saving and helps users achieve their financial goals.
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
        ('groceries',    'Groceries'),
        ('vacation',      'Vacation Fund'),
        ('education',     'Education Fund'),
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
    is_locked    = models.BooleanField( # Locked pockets are for specific purposes like rent or deposits that shouldn't be withdrawn manually. They can only be debited by the system when a payment is due, ensuring funds are reserved for their intended use.
        default=True, # the default is True to encourage users to use pockets for their intended purpose and prevent accidental withdrawals. Users can unlock pockets if they want more flexibility, but locking by default promotes disciplined saving.
        help_text='Locked pockets cannot be withdrawn from manually',
    )
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)


    locked_at    = models.DateTimeField( # When a pocket is locked, we record the timestamp. This can be useful for enforcing policies such as a minimum lock period (3 days) before a pocket can be unlocked, or for tracking how long funds have been reserved for their intended purpose.
    null=True,
    blank=True,
    help_text='When the pocket was locked',
    )
    unlock_requested_at    = models.DateTimeField( 
        # When a user requests to unlock a pocket, we record the timestamp. The pocket remains locked for a predefined period (e.g., 3 days) after the request to encourage users to reconsider unlocking and to prevent impulsive spending. 
        # After the waiting period, the system can automatically unlock the pocket, or an admin can review and approve the unlock request.
        null=True,
        blank=True,
        help_text='When the user requested an unlock',
    )
    unlock_available_at    = models.DateTimeField( 
        # This field indicates when the pocket becomes available for unlocking after the user has requested it. 
        # For example, if the policy is to have a 3-day waiting period after an unlock request, this field would be set to the timestamp of the unlock request plus 3 days. 
        # This allows the system to automatically determine when a pocket can be unlocked and helps enforce the waiting period.
        null=True,
        blank=True,
        help_text='When the pocket becomes unlockable (3 days after request)',
    )


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

    # The unlock status can be 'locked' (default state), 'unlock_pending' (after user requests unlock but before waiting period ends), 
    # 'ready_to_unlock' (waiting period has passed and pocket can be unlocked), or 'unlocked' (pocket is currently unlocked). 
    # This property helps the frontend display the correct status and available actions for each pocket.
    @property
    def unlock_status(self):
        from django.utils import timezone
        if not self.is_locked:
            return 'unlocked'
        if not self.unlock_requested_at:
            return 'locked'
        if timezone.now() >= self.unlock_available_at:
            return 'ready_to_unlock'
        return 'unlock_pending'

    @property
    def hours_until_unlock(self):
        from django.utils import timezone
        if not self.unlock_available_at:
            return None
        remaining = self.unlock_available_at - timezone.now()
        if remaining.total_seconds() <= 0:
            return 0
        return round(remaining.total_seconds() / 3600, 1)


    # The credit and debit methods allow us to add or remove funds from the pocket while ensuring that the balance is updated correctly.
    def credit(self, amount, save=True):
        """Add money into the pocket."""
        self.balance += amount
        if save:
            self.save(update_fields=['balance'])

    def debit(self, amount, save=True):
        """
        Remove money from pocket.
        Blocks if pocket is locked.
        Blocks if insufficient balance.
        """
        if self.is_locked:
            raise ValueError(
                'This pocket is locked and cannot be withdrawn from. '
                'Request an unlock first.'
            )
        if self.balance < amount:
            raise ValueError(
                f'Insufficient pocket balance. '
                f'Available: ₦{self.balance:,}, Required: ₦{amount:,}'
            )
        self.balance -= amount
        if save:
            self.save(update_fields=['balance'])

    def request_unlock(self, bypass_wait=False):
        """
        User requests to unlock a pocket.
        Sets a 3-day waiting period before
        the pocket can actually be unlocked.

        bypass_wait=True is for dev/testing only.
        Remove True in production. Never pass True
        """
        from django.utils import timezone
        from datetime import timedelta

        if not self.is_locked:
            raise ValueError('This pocket is not locked.')

        if self.pocket_type == 'credit_vault':
            raise ValueError(
                'Credit Builder Vault cannot be unlocked manually. '
                'It releases automatically when your loan completes.'
            )

        if bypass_wait:
            # Dev mode — unlock immediately
            self.is_locked           = False
            self.unlock_requested_at = timezone.now()
            self.unlock_available_at = timezone.now()
            self.save(update_fields=[
                'is_locked',
                'unlock_requested_at',
                'unlock_available_at',
            ])
            return True, 'Pocket unlocked immediately (dev mode).'

        # Production — set 3-day countdown
        now = timezone.now()
        self.unlock_requested_at = now
        self.unlock_available_at = now + timedelta(days=3)
        self.save(update_fields=[
            'unlock_requested_at',
            'unlock_available_at',
        ])
        return False, (
            f'Unlock requested. Your pocket will be available '
            f'to unlock on '
            f'{self.unlock_available_at.strftime("%b %d, %Y at %H:%M")}.'
        )

    def confirm_unlock(self):
        """
        Called after the 3-day wait has passed.
        Actually unlocks the pocket.
        """
        from django.utils import timezone

        if not self.unlock_available_at:
            raise ValueError(
                'No unlock has been requested for this pocket.'
            )

        if timezone.now() < self.unlock_available_at:
            remaining = self.unlock_available_at - timezone.now()
            hours     = int(remaining.total_seconds() / 3600)
            raise ValueError(
                f'Pocket cannot be unlocked yet. '
                f'{hours} hour(s) remaining.'
            )

        self.is_locked           = False
        self.unlock_requested_at = None
        self.unlock_available_at = None
        self.save(update_fields=[
            'is_locked',
            'unlock_requested_at',
            'unlock_available_at',
        ])
        return True, 'Pocket unlocked successfully.'



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