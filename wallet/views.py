from django.shortcuts import render
from rest_framework              import status
from rest_framework.views        import APIView
from rest_framework.response     import Response
from rest_framework.permissions  import IsAuthenticated, AllowAny
from django.conf                 import settings
import hashlib
import json

from .models   import Wallet, SavingsPocket, Transaction
from .services import WalletService, FlutterwaveService
from .serializers import (
    WalletSerializer,
    WalletSummarySerializer,
    SavingsPocketSerializer,
    SavingsPocketCreateSerializer,
    TransactionSerializer,
    FundPocketSerializer,
    WithdrawPocketSerializer,
)


class WalletView(APIView):
    """
    GET  — returns wallet details including
           virtual account and all pockets.
    Creates the wallet and virtual account
    automatically if they don't exist yet.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        currency = request.query_params.get('currency', 'NGN')

        if currency not in settings.WALLET_CURRENCIES:
            return Response(
                {'error': f'Unsupported currency: {currency}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet, created = WalletService.get_or_create_wallet(
            request.user, currency
        )

        # Auto-create virtual account if missing
        if not hasattr(wallet, 'virtual_account'):
            try:
                FlutterwaveService.create_virtual_account(
                    wallet, request.user
                )
            except Exception:
                pass   # non-blocking — show wallet without VA

        serializer = WalletSerializer(wallet)
        return Response({
            'wallet':    serializer.data,
            'is_new':    created,
        })


class WalletSummaryView(APIView):
    """
    GET — lightweight wallet summary
    for the home dashboard widget.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallets = Wallet.objects.filter(
            user=request.user,
            is_active=True,
        )
        if not wallets.exists():
            # Auto-create NGN wallet
            wallet, _ = WalletService.get_or_create_wallet(request.user)
            wallets   = Wallet.objects.filter(user=request.user)

        serializer = WalletSummarySerializer(wallets, many=True)
        return Response({'wallets': serializer.data})


class TransactionListView(APIView):
    """
    GET — paginated transaction history
    for the current user's wallet.
    Filterable by currency and type.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        currency = request.query_params.get('currency', 'NGN')
        tx_type  = request.query_params.get('type', None)

        try:
            wallet = Wallet.objects.get(
                user=request.user,
                currency=currency,
            )
        except Wallet.DoesNotExist:
            return Response(
                {'error': 'Wallet not found. Please open your wallet first.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        transactions = wallet.transactions.all()

        if tx_type:
            transactions = transactions.filter(transaction_type=tx_type)

        serializer = TransactionSerializer(transactions[:50], many=True)
        return Response({
            'currency':     currency,
            'balance':      wallet.balance,
            'transactions': serializer.data,
        })


class SavingsPocketListCreateView(APIView):
    """
    GET  — list all savings pockets on NGN wallet
    POST — create a new savings pocket
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, _ = WalletService.get_or_create_wallet(request.user)
        pockets   = wallet.pockets.filter(is_active=True)
        serializer = SavingsPocketSerializer(pockets, many=True)
        return Response({'pockets': serializer.data})

    def post(self, request):
        serializer = SavingsPocketCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet, _ = WalletService.get_or_create_wallet(request.user)

        # Max 5 pockets per wallet
        if wallet.pockets.filter(is_active=True).count() >= 5:
            return Response(
                {'error': 'Maximum of 5 savings pockets allowed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pocket = WalletService.create_pocket(
            wallet       = wallet,
            name         = serializer.validated_data['name'],
            pocket_type  = serializer.validated_data['pocket_type'],
            target_amount = serializer.validated_data.get('target_amount'),
        )

        return Response(
            SavingsPocketSerializer(pocket).data,
            status=status.HTTP_201_CREATED,
        )


class FundPocketView(APIView):
    """
    POST — move money from main wallet
    balance into a savings pocket.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FundPocketSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet, _ = WalletService.get_or_create_wallet(request.user)
        amount    = serializer.validated_data['amount']

        try:
            pocket = wallet.pockets.get(
                id=serializer.validated_data['pocket_id'],
                is_active=True,
            )
        except SavingsPocket.DoesNotExist:
            return Response(
                {'error': 'Pocket not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            transaction = WalletService.transfer_to_pocket(
                wallet, pocket, amount
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'message':        f'₦{amount:,} moved to {pocket.name}.',
            'wallet_balance': wallet.balance,
            'pocket_balance': pocket.balance,
            'reference':      transaction.reference,
        })


class WithdrawPocketView(APIView):
    """
    POST — move money from a savings pocket
    back to the main wallet balance.
    Locked pockets (e.g. credit vault) cannot
    be withdrawn from manually.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WithdrawPocketSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet, _ = WalletService.get_or_create_wallet(request.user)
        amount    = serializer.validated_data['amount']

        try:
            pocket = wallet.pockets.get(
                id=serializer.validated_data['pocket_id'],
                is_active=True,
            )
        except SavingsPocket.DoesNotExist:
            return Response(
                {'error': 'Pocket not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            transaction = WalletService.withdraw_from_pocket(
                wallet, pocket, amount
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'message':        f'₦{amount:,} withdrawn from {pocket.name}.',
            'wallet_balance': wallet.balance,
            'pocket_balance': pocket.balance,
            'reference':      transaction.reference,
        })


# The RequestPocketUnlockView and ConfirmPocketUnlockView handle the process of unlocking a locked savings pocket. 
# When a user requests to unlock a pocket, it starts a 3-day countdown during which the pocket remains locked. 
# After the waiting period has passed, the user can confirm the unlock, at which point the pocket becomes unlocked and funds can be withdrawn from it. 
# This is designed to encourage commitment to saving by preventing impulsive withdrawals from locked pockets.
class RequestPocketUnlockView(APIView):
    """
    POST — user requests to unlock a savings pocket.
    Starts the 3-day countdown.
    In dev mode, pass bypass_wait: true to unlock immediately.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .serializers import UnlockRequestSerializer
        serializer = UnlockRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet, _ = WalletService.get_or_create_wallet(request.user)

        try:
            pocket = wallet.pockets.get(
                id=serializer.validated_data['pocket_id'],
                is_active=True,
            )
        except SavingsPocket.DoesNotExist:
            return Response(
                {'error': 'Pocket not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        bypass_wait = serializer.validated_data.get('bypass_wait', False)

        # Only allow bypass in DEBUG mode
        from django.conf import settings
        if bypass_wait and not settings.DEBUG:
            bypass_wait = False

        try:
            unlocked, message = pocket.request_unlock(
                bypass_wait=bypass_wait
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'message':            message,
            'unlocked':           unlocked,
            'unlock_status':      pocket.unlock_status,
            'unlock_available_at': pocket.unlock_available_at,
            'hours_until_unlock': pocket.hours_until_unlock,
        })


class ConfirmPocketUnlockView(APIView):
    """
    POST — confirms the unlock after the 3-day
    wait has passed. Only works if enough time
    has elapsed since the unlock was requested.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pocket_id = request.data.get('pocket_id')
        if not pocket_id:
            return Response(
                {'error': 'pocket_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet, _ = WalletService.get_or_create_wallet(request.user)

        try:
            pocket = wallet.pockets.get(
                id=pocket_id,
                is_active=True,
            )
        except SavingsPocket.DoesNotExist:
            return Response(
                {'error': 'Pocket not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            _, message = pocket.confirm_unlock()
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'message':       message,
            'unlock_status': pocket.unlock_status,
            'is_locked':     pocket.is_locked,
        })



# This view handles incoming webhooks from Flutterwave for payment events. 
# It verifies the signature to ensure the request is legitimate, then processes the event (e.g. crediting the wallet when a charge is completed). This endpoint must be publicly accessible and should be registered in the Flutterwave dashboard to receive events.
class FlutterwaveWebhookView(APIView):
    """
    POST — receives Flutterwave webhook events.
    Verifies signature, processes payment,
    and credits the appropriate wallet.
    This endpoint must be PUBLIC (no auth).
    TO DO - Register this URL in our Flutterwave dashboard.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Verify webhook signature
        signature = request.headers.get('verif-hash', '')
        if signature != settings.FLUTTERWAVE_WEBHOOK_SECRET:
            return Response(
                {'error': 'Invalid signature.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        payload = request.data
        event   = payload.get('event')

        if event == 'charge.completed':
            return self._handle_charge(payload)

        if event == 'transfer.completed':
            return self._handle_transfer(payload)

        # Unknown event — acknowledge and ignore
        return Response({'status': 'acknowledged'})


    def _handle_charge(self, payload):
        """Handle incoming payment to virtual account."""
        data = payload.get('data', {})

        if data.get('status') != 'successful':
            return Response({'status': 'ignored — not successful'})

        # Find the wallet by virtual account number
        account_number = data.get('virtual_account', {}).get(
            'account_number', ''
        )

        try:
            from .models import VirtualAccount
            va     = VirtualAccount.objects.get(
                account_number=account_number
            )
            wallet = va.wallet
        except Exception:
            return Response({'status': 'wallet not found'})

        amount       = data.get('amount', 0)
        provider_ref = data.get('flw_ref', '')

        # Prevent duplicate processing
        if Transaction.objects.filter(provider_ref=provider_ref).exists():
            return Response({'status': 'already processed'})

        WalletService.credit_wallet(
            wallet           = wallet,
            amount           = amount,
            transaction_type = 'credit',
            description      = 'Wallet funded via bank transfer',
            provider_ref     = provider_ref,
            provider         = 'flutterwave',
        )

        return Response({'status': 'success'})

# The _handle_transfer method is a placeholder for handling outgoing transfer confirmations from Flutterwave.
# This would be used if we implement features that involve sending money out of the wallet (e.g. payouts to landlords). 
# For now, it simply acknowledges the event without taking action.
    def _handle_transfer(self, payload):
        """Handle outgoing transfer confirmation."""
        # Mark related transaction as completed
        return Response({'status': 'acknowledged'})