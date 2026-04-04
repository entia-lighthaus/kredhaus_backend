from rest_framework import serializers
from .models import Wallet, SavingsPocket, Transaction, VirtualAccount

# Serializers for wallet API endpoints. These convert model instances to JSON and validate incoming data for creating/updating wallets, transactions, and savings pockets.
class VirtualAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model  = VirtualAccount
        fields = [
            'account_number',
            'bank_name',
            'account_name',
        ]
        read_only_fields = fields


# SavingsPocketSerializer is used to represent the savings pockets in the wallet. It includes read-only fields for progress percentage, unlock status, and hours until unlock, which are calculated properties based on the pocket's balance and target amount, as well as its lock status and unlock request timestamps.
# The progress_percent field calculates how close the pocket is to its target amount, while unlock_status and hours_until_unlock provide information about the lock status of the pocket and how long until it can be unlocked if it's currently locked.
class SavingsPocketSerializer(serializers.ModelSerializer):
    progress_percent  = serializers.ReadOnlyField()
    unlock_status     = serializers.ReadOnlyField()
    hours_until_unlock = serializers.ReadOnlyField()

    class Meta:
        model  = SavingsPocket
        fields = [
            'id',
            'name',
            'pocket_type',
            'balance',
            'target_amount',
            'progress_percent',
            'is_locked',
            'unlock_status',
            'hours_until_unlock',
            'unlock_requested_at',
            'unlock_available_at',
            'is_active',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'balance',
            'progress_percent',
            'unlock_status',
            'hours_until_unlock',
            'created_at',
        ]



class SavingsPocketCreateSerializer(serializers.Serializer):
    name          = serializers.CharField(max_length=64)
    pocket_type   = serializers.ChoiceField(
        choices=[
            'rent', 'home_deposit', 'emergency',
            'utility', 'custom',
        ],
        default='custom',
    )
    target_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
    )

    def validate_target_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                'Target amount must be greater than zero.'
            )
        return value


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Transaction
        fields = [
            'id',
            'transaction_type',
            'amount',
            'currency',
            'balance_before',
            'balance_after',
            'status',
            'reference',
            'description',
            'provider_ref',
            'created_at',
        ]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    virtual_account = VirtualAccountSerializer(read_only=True)
    pockets         = SavingsPocketSerializer(many=True, read_only=True)
    owner_name      = serializers.SerializerMethodField()

    class Meta:
        model  = Wallet
        fields = [
            'id',
            'owner_name',
            'currency',
            'balance',
            'ledger_balance',
            'virtual_account',
            'pockets',
            'is_active',
            'created_at',
        ]
        read_only_fields = fields

    def get_owner_name(self, obj):
        return f'{obj.user.first_name} {obj.user.last_name}'


class WalletSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight wallet summary for dashboard.
    Does not include full transaction history.
    """
    virtual_account  = VirtualAccountSerializer(read_only=True)
    total_in_pockets = serializers.SerializerMethodField()
    pockets_count    = serializers.SerializerMethodField()

    class Meta:
        model  = Wallet
        fields = [
            'id',
            'currency',
            'balance',
            'ledger_balance',
            'total_in_pockets',
            'pockets_count',
            'virtual_account',
        ]
        read_only_fields = fields

    def get_total_in_pockets(self, obj):
        return sum(p.balance for p in obj.pockets.filter(is_active=True))

    def get_pockets_count(self, obj):
        return obj.pockets.filter(is_active=True).count()



# These serializers are used for fund and withdraw operations on savings pockets.
# They are separate from the main SavingsPocketSerializer to allow for specific validation and to keep the main serializer focused on representing the pocket data structure.
class FundPocketSerializer(serializers.Serializer):
    pocket_id = serializers.UUIDField()
    amount    = serializers.DecimalField(max_digits=14, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Amount must be greater than zero.'
            )
        return value



# WithdrawPocketSerializer is separate from FundPocketSerializer to allow for different validation rules or business logic in the future 
# (e.g. checking if the pocket has sufficient balance before allowing a withdrawal).
class WithdrawPocketSerializer(serializers.Serializer):
    pocket_id = serializers.UUIDField()
    amount    = serializers.DecimalField(max_digits=14, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Amount must be greater than zero.'
            )
        return value
    
# UnlockRequestSerializer is used when a user wants to unlock a locked savings pocket. 
# It includes a bypass_wait field for development/testing purposes, which should always be False in production to enforce the 3-day waiting period before a pocket can be unlocked.
class UnlockRequestSerializer(serializers.Serializer):
    pocket_id   = serializers.UUIDField()
    bypass_wait = serializers.BooleanField(
        default=False,
        help_text='Dev only — bypasses the 3-day wait. '
                  'Always False in production.',
    )