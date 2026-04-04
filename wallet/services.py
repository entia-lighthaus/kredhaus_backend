import uuid
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import Wallet, SavingsPocket, Transaction, VirtualAccount


def generate_reference(prefix='KH'):
    """Generate a unique transaction reference."""
    # Format: PREFIX-XXXXXXXXXXXX (12 random chars)
    # Using UUID4 and slicing for simplicity, but could be replaced with a more compact generator if needed.
    return f'{prefix}-{str(uuid.uuid4()).upper()[:12]}'


class WalletService:
    # This service class provides static methods for wallet operations,
    # such as creating wallets, crediting/debiting, and handling pockets.
    # All wallet-related business logic should go here to keep views thin and models focused on data structure.
    # For example, when a user makes a payment, the view would call WalletService.credit_wallet() to handle the logic of updating balances and recording transactions.

    @staticmethod
    def get_or_create_wallet(user, currency='NGN'):
        """
        Get existing wallet or create one.
        Called automatically on first login
        or when user accesses wallet screen.
        """
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            currency=currency,
        )
        return wallet, created

    @staticmethod
    def credit_wallet(wallet, amount, transaction_type,
                      description='', provider_ref='',
                      provider='', metadata=None):
        """
        Credit a wallet and record the transaction.
        This is the single entry point for all credits.
        """
        amount          = Decimal(str(amount))
        balance_before  = wallet.balance
        wallet.credit(amount)
        balance_after   = wallet.balance

        transaction = Transaction.objects.create(
            wallet           = wallet,
            transaction_type = transaction_type,
            amount           = amount,
            currency         = wallet.currency,
            balance_before   = balance_before,
            balance_after    = balance_after,
            status           = 'completed',
            reference        = generate_reference(),
            description      = description,     
            provider_ref     = provider_ref, # External payment reference (e.g. Flutterwave transaction ID) 
            provider         = provider,       
            metadata         = metadata or {},
        )
        return transaction


    # The debit_wallet method is separate to ensure that we can handle insufficient balance cases cleanly, and to keep the logic straightforward. 
    # It raises a ValueError if the wallet does not have enough balance, which the calling code can catch and respond to (e.g. by showing an error message to the user).
    @staticmethod
    def debit_wallet(wallet, amount, transaction_type,
                     description='', metadata=None):
      
        amount          = Decimal(str(amount))
        balance_before  = wallet.balance
        wallet.debit(amount)
        balance_after   = wallet.balance

        transaction = Transaction.objects.create(
            wallet           = wallet,
            transaction_type = transaction_type,
            amount           = amount,
            currency         = wallet.currency,
            balance_before   = balance_before,
            balance_after    = balance_after,
            status           = 'completed',
            reference        = generate_reference(),
            description      = description,
            metadata         = metadata or {},
        )
        return transaction

    @staticmethod
    def transfer_to_pocket(wallet, pocket, amount, description=''):
        """
        Move funds from main wallet balance
        into a savings pocket.
        """
        amount = Decimal(str(amount))

        if not wallet.can_debit(amount):
            raise ValueError('Insufficient wallet balance to fund pocket.')

        # Debit main wallet
        wallet.debit(amount)

        # Credit pocket
        pocket.credit(amount)

        # Record transaction
        transaction = Transaction.objects.create(
            wallet           = wallet,
            transaction_type = 'savings_deposit',
            amount           = amount,
            currency         = wallet.currency,
            balance_before   = wallet.balance + amount,
            balance_after    = wallet.balance,
            status           = 'completed',
            reference        = generate_reference('KH-SAV'),
            description      = description or f'Transfer to {pocket.name}',
            related_pocket   = pocket,
        )
        return transaction

    @staticmethod
    def withdraw_from_pocket(wallet, pocket, amount, description=''):
        """
        Move funds from a savings pocket
        back to the main wallet balance.
        """
        amount = Decimal(str(amount))
        pocket.debit(amount)   # raises if locked or insufficient
        wallet.credit(amount)

        transaction = Transaction.objects.create(
            wallet           = wallet,
            transaction_type = 'savings_withdraw',
            amount           = amount,
            currency         = wallet.currency,
            balance_before   = wallet.balance - amount,
            balance_after    = wallet.balance,
            status           = 'completed',
            reference        = generate_reference('KH-WIT'),
            description      = description or f'Withdrawal from {pocket.name}',
            related_pocket   = pocket,
        )
        return transaction

    @staticmethod
    def create_pocket(wallet, name, pocket_type='custom',
                      target_amount=None, is_locked=False):
        """Create a new savings pocket on a wallet."""
        pocket = SavingsPocket.objects.create(
            wallet        = wallet,
            name          = name,
            pocket_type   = pocket_type,
            target_amount = target_amount,
            is_locked     = is_locked,
        )
        return pocket


class FlutterwaveService:
    """
    Handles all Flutterwave API interactions.
    In development, methods return mock responses
    when FLUTTERWAVE_SECRET_KEY is not set.
    """

    BASE_URL = 'https://api.flutterwave.com/v3'

    @classmethod
    def _headers(cls):
        return {
            'Authorization': f'Bearer {settings.FLUTTERWAVE_SECRET_KEY}',
            'Content-Type':  'application/json',
        }

    @classmethod
    def _is_mock(cls):
        return not settings.FLUTTERWAVE_SECRET_KEY

    @classmethod
    def create_virtual_account(cls, wallet, user):
        """
        Create a Flutterwave virtual account
        for the wallet so users can fund
        via bank transfer.
        """
        if cls._is_mock():
            # Return mock data for development
            mock_account = VirtualAccount.objects.create(
                wallet          = wallet,
                account_number  = f'909{user.id}'[:10],
                bank_name       = 'Wema Bank (Mock)',
                account_name    = (
                    f'{user.first_name} {user.last_name} / Kredhaus'
                ),
                flutterwave_ref = f'MOCK-{uuid.uuid4()}',
            )
            wallet.virtual_account_number = mock_account.account_number
            wallet.virtual_bank_name      = mock_account.bank_name
            wallet.save(update_fields=[
                'virtual_account_number',
                'virtual_bank_name',
            ])
            return mock_account

        # Production Flutterwave call
        try:
            payload = {
                'email':       user.email or f'{user.phone}@kredhaus.app',
                'is_permanent': True,
                'bvn':          user.bvn or '',
                'tx_ref':       generate_reference('KH-VA'),
                'phonenumber':  user.phone,
                'firstname':    user.first_name,
                'lastname':     user.last_name,
                'narration':    f'{user.first_name} {user.last_name} / Kredhaus',
            }
            response = requests.post(
                f'{cls.BASE_URL}/virtual-account-numbers',
                json    = payload,
                headers = cls._headers(),
                timeout = 15,
            )
            data = response.json()

            if data.get('status') == 'success':
                acct = data['data']
                virtual_account = VirtualAccount.objects.create(
                    wallet          = wallet,
                    account_number  = acct['account_number'],
                    bank_name       = acct['bank_name'],
                    account_name    = acct['account_name'],
                    flutterwave_ref = acct.get('flw_ref', ''),
                )
                wallet.virtual_account_number = acct['account_number']
                wallet.virtual_bank_name      = acct['bank_name']
                wallet.flutterwave_ref        = acct.get('flw_ref', '')
                wallet.save(update_fields=[
                    'virtual_account_number',
                    'virtual_bank_name',
                    'flutterwave_ref',
                ])
                return virtual_account

        except Exception as e:
            raise ValueError(f'Flutterwave virtual account creation failed: {e}')

    @classmethod
    def verify_transaction(cls, transaction_id):
        """
        Verify a Flutterwave transaction by ID.
        Called from the webhook handler.
        """
        if cls._is_mock():
            return {'status': 'successful', 'amount': 5000, 'currency': 'NGN'}

        try:
            response = requests.get(
                f'{cls.BASE_URL}/transactions/{transaction_id}/verify',
                headers = cls._headers(),
                timeout = 15,
            )
            return response.json().get('data', {})
        except Exception as e:
            raise ValueError(f'Transaction verification failed: {e}')

    @classmethod
    def initiate_transfer(cls, amount, bank_code,
                          account_number, account_name,
                          narration='Kredhaus payout'):
        """
        Send money from Kredhaus Flutterwave
        balance to a bank account.
        Used for landlord withdrawals.
        """
        if cls._is_mock():
            return {
                'status':    'success',
                'reference': generate_reference('KH-PAY'),
            }

        try:
            payload = {
                'account_bank':   bank_code,
                'account_number': account_number,
                'amount':         float(amount),
                'narration':      narration,
                'currency':       'NGN',
                'reference':      generate_reference('KH-PAY'),
                'callback_url':   f'{settings.BASE_URL}/api/v1/wallet/webhook/',
                'debit_currency': 'NGN',
            }
            response = requests.post(
                f'{cls.BASE_URL}/transfers',
                json    = payload,
                headers = cls._headers(),
                timeout = 15,
            )
            return response.json()
        except Exception as e:
            raise ValueError(f'Transfer initiation failed: {e}')