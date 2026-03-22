from rest_framework import serializers
from .models import User, Referee
from django.contrib.auth import authenticate
from django.conf import settings


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


# creating a protected endpoint
# This endpoint returns the currently logged-in user's profile. It's protected, meaning if you call it without a valid token, it rejects you

class UserProfileSerializer(serializers.ModelSerializer):

    kyc_tier_label   = serializers.CharField(
        source='get_kyc_tier_display',
        read_only=True
    )
    kyc_unlocks      = serializers.SerializerMethodField()
    onboarding_steps = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'phone',
            'first_name',
            'last_name',
            'email',
            'role',
            'kyc_tier',
            'kyc_tier_label',
            'kyc_unlocks',
            'nin_verified',
            'bvn_verified',
            'phone_verified',
            'onboarding_steps',
            'date_joined',
        ]

    def get_kyc_unlocks(self, obj):
        """
        Returns the list of features the user
        can currently access based on their tier.
        """
        unlocks = []
        for tier in range(obj.kyc_tier + 1):
            unlocks += settings.KYC_TIER_PERMISSIONS.get(tier, [])
        return unlocks

    def get_onboarding_steps(self, obj):
        """
        Returns the status of each onboarding step
        so the frontend knows what still needs to be done.
        """
        return {
            'phone_verified':  obj.phone_verified,
            'nin_verified':    obj.nin_verified,
            'bvn_verified':    obj.bvn_verified,
            'kyc_tier':        obj.kyc_tier,
            'profile_complete': all([
                obj.phone_verified,
                obj.nin_verified,
                obj.first_name,
                obj.last_name,
            ])
        }


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


# The RefereeSerializer identifies attached references for tenancies
class RefereeSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Referee
        fields = [
            'id',
            'full_name',
            'phone',
            'email',
            'occupation',
            'relationship',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class EmergencyContactSerializer(serializers.Serializer):
    emergency_name         = serializers.CharField(max_length=128)
    emergency_phone        = serializers.CharField(max_length=20)
    emergency_relationship = serializers.CharField(max_length=64)


class ProfilePhotoSerializer(serializers.ModelSerializer):

    class Meta:
        model  = User
        fields = ['profile_photo']

    def validate_profile_photo(self, value):
        # Limit file size to 5MB
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                'Profile photo must be smaller than 5MB.'
            )
        # Allow only image types
        allowed = ['image/jpeg', 'image/png', 'image/jpg']
        if value.content_type not in allowed:
            raise serializers.ValidationError(
                'Only JPEG and PNG images are accepted.'
            )
        return value


class ProfileCompletionSerializer(serializers.ModelSerializer):
    """
    Returns the full profile completion breakdown.
    Used by the frontend to drive the progress bar.
    """
    referees           = RefereeSerializer(many=True, read_only=True)
    completion_breakdown = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'profile_completion',
            'profile_photo',
            'first_name',
            'last_name',
            'email',
            'phone_verified',
            'nin_verified',
            'bvn_verified',
            'kyc_tier',
            'emergency_name',
            'emergency_phone',
            'emergency_relationship',
            'referees',
            'completion_breakdown',
        ]

    # This method calculates which parts of the profile are complete and how many points each part is worth.
    def get_completion_breakdown(self, obj):
        return {
            'basic_info': {
                'complete': bool(obj.first_name and obj.last_name),
                'points':   10,
            },
            'email_added': {
                'complete': bool(obj.email),
                'points':   5,
            },
            'profile_photo': {
                'complete': bool(obj.profile_photo),
                'points':   5,
            },
            'phone_verified': {
                'complete': obj.phone_verified,
                'points':   10,
            },
            'nin_verified': {
                'complete': obj.nin_verified,
                'points':   10,
            },
            'bvn_verified': {
                'complete': obj.bvn_verified,
                'points':   10,
            },
            'kyc_tier_1': {
                'complete': obj.kyc_tier >= 1,
                'points':   10,
            },
            'kyc_tier_2': {
                'complete': obj.kyc_tier >= 2,
                'points':   10,
            },
            'emergency_contact': {
                'complete': bool(
                    obj.emergency_name and obj.emergency_phone
                ),
                'points':   15,
            },
            'referee_1': {
                'complete': obj.referees.count() >= 1,
                'points':   10,
            },
            'referee_2': {
                'complete': obj.referees.count() >= 2,
                'points':   5,
            },
        }
    

# serializers to handle device authentiction
class SetPINSerializer(serializers.Serializer): 
    pin         = serializers.CharField(
        min_length=4,
        max_length=6,
        write_only=True,
    )
    confirm_pin = serializers.CharField(
        min_length=4,
        max_length=6,
        write_only=True,
    )

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'PIN must contain digits only.'
            )
        # Block obvious PINs
        blocked = ['0000', '1234', '1111', '0000', '9999']
        if value in blocked:
            raise serializers.ValidationError(
                'This PIN is too simple. Please choose a stronger PIN.'
            )
        return value

    def validate(self, attrs):
        if attrs['pin'] != attrs['confirm_pin']:
            raise serializers.ValidationError(
                {'confirm_pin': 'PINs do not match.'}
            )
        return attrs


class PINLoginSerializer(serializers.Serializer):
    phone     = serializers.CharField()
    pin       = serializers.CharField(
        min_length=4,
        max_length=6,
        write_only=True,
    )
    device_id = serializers.CharField()