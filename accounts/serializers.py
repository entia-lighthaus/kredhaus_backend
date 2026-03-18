from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate


class RegisterSerializer(serializers.ModelSerializer):

    password         = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = [
            'phone',
            'first_name',
            'last_name',
            'email',
            'role',
            'password',
            'confirm_password',
        ]

    def validate_phone(self, value):
        # Normalise: if starts with 0, replace with +234
        value = value.strip()
        if value.startswith('0'):
            value = '+234' + value[1:]
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('confirm_password'):
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user     = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    


class LoginSerializer(serializers.Serializer):

    phone    = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone    = attrs.get('phone')
        password = attrs.get('password')

        # Normalise phone
        if phone.startswith('0'):
            phone = '+234' + phone[1:]

        # authenticate() checks the password against the hashed version in the DB
        user = authenticate(username=phone, password=password)

        if not user:
            raise serializers.ValidationError('Invalid phone number or password.')

        if not user.is_active:
            raise serializers.ValidationError('This account has been deactivated.')

        attrs['user'] = user
        return attrs


#creating a protected endpoint
# This endpoint returns the currently logged-in user's profile. It's protected, meaning if you call it without a valid token, it rejects you.
class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model  = User
        fields = [
            'phone',
            'first_name',
            'last_name',
            'email',
            'role',
            'nin_verified',
            'bvn_verified',
            'phone_verified',
            'date_joined',
        ]


# NIN and BVN serializers.
# They validate input only, they don't map directly to a model. This is the right pattern for action-based endpoints like verification.
class NINVerificationSerializer(serializers.Serializer):
    nin = serializers.CharField(min_length=11, max_length=11)

    def validate_nin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'NIN must be 11 digits with no letters or spaces.'
            )
        return value


class BVNVerificationSerializer(serializers.Serializer):
    bvn = serializers.CharField(min_length=11, max_length=11)

    def validate_bvn(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'BVN must be 11 digits with no letters or spaces.'
            )
        return value
    

# KYC Serializers
class KYCTier1Serializer(serializers.Serializer):
    """
    Tier 1 requires phone + NIN.
    Phone is already verified at registration.
    NIN is submitted here.
    """
    nin = serializers.CharField(min_length=11, max_length=11)

    def validate_nin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'NIN must be 11 digits, numbers only.'
            )
        return value


class KYCTier2Serializer(serializers.Serializer):
    """
    Tier 2 requires BVN + address.
    """
    bvn           = serializers.CharField(min_length=11, max_length=11)
    address_line1 = serializers.CharField(max_length=255)
    address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    lga           = serializers.CharField(max_length=64)
    state         = serializers.CharField(max_length=64)

    def validate_bvn(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'BVN must be 11 digits, numbers only.'
            )
        return value


class KYCTier3Serializer(serializers.Serializer):
    """
    Tier 3 requires income proof + NOK + employment.
    """
    employer_name    = serializers.CharField(max_length=128)
    monthly_income   = serializers.DecimalField(max_digits=12, decimal_places=2)
    nok_name         = serializers.CharField(max_length=128) #NOK = Next of Kin
    nok_phone        = serializers.CharField(max_length=20)
    nok_relationship = serializers.CharField(max_length=64)

    def validate_monthly_income(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Monthly income must be greater than zero.'
            )
        return value


class KYCStatusSerializer(serializers.ModelSerializer):
    """
    Returns the user's current KYC state —
    what tier they are on and what they have completed.
    """
    kyc_tier_label     = serializers.CharField(
        source='get_kyc_tier_display',
        read_only=True
    )
    tier_qualified_for = serializers.IntegerField(
        source='get_kyc_requirements_met',
        read_only=True
    )

    class Meta:
        model  = User
        fields = [
            'kyc_tier',
            'kyc_tier_label',
            'tier_qualified_for',
            'phone_verified',
            'nin_verified',
            'bvn_verified',
            'address_line1',
            'lga',
            'state',
            'nok_name',
            'monthly_income',
        ]