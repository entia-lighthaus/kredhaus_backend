from rest_framework import serializers

from django.contrib.auth import authenticate
from django.conf import settings
import hashlib

from .models import User, UserProfile, ReferralCredit, DeviceSession


# ══════════════════════════════════════════════════════════════════════════
# AUTH SERIALIZERS
# ═════════════════════════════════════════════════════════════════════════

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
        
        if phone.startswith('0'):
            phone = '+234' + phone[1:]

        
        user = authenticate(username=phone, password=password)

        if not user:
            raise serializers.ValidationError(
                'Invalid phone number or password.'
            )
        if not user.is_active:
            raise serializers.ValidationError(
                'This account has been deactivated.'
            )

        attrs['user'] = user
        return attrs


# ══════════════════════════════════════════════════════════════════════════
# USER PROFILE SERIALIZERS
# ══════════════════════════════════════════════════════════════════════════

class BasicUserSerializer(serializers.ModelSerializer):
    """
    Lightweight user info — returned after login
    and on protected /profile/ endpoint.
    Includes KYC status and onboarding progress.
    """
    kyc_tier_label   = serializers.CharField(
        source='get_kyc_tier_display',
        read_only=True,
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
            'profile_completion',
            'referral_code',
            'onboarding_steps',
            'date_joined',
        ]

    def get_kyc_unlocks(self, obj):
        
        unlocks = []
        for tier in range(obj.kyc_tier + 1):
            unlocks += settings.KYC_TIER_PERMISSIONS.get(tier, [])
        return unlocks

    def get_onboarding_steps(self, obj):
        
        return {
            'phone_verified':   obj.phone_verified,
            'nin_verified':     obj.nin_verified,
            'bvn_verified':     obj.bvn_verified,
            'kyc_tier':         obj.kyc_tier,
            'profile_complete': all([
                obj.phone_verified,
                obj.nin_verified,
                obj.first_name,
                obj.last_name,
            ]),
        }


class ExtendedProfileSerializer(serializers.ModelSerializer):
    """
    Full UserProfile data — employment, emergency
    contact, referees, bio.
    Used by the profile builder screens.
    """
    # Read employer_name and monthly_income from User
    # since they live there (set during KYC Tier 3)
    employer_name  = serializers.CharField(
        source='user.employer_name',
        read_only=True,
    )
    monthly_income = serializers.DecimalField(
        source='user.monthly_income',
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    completion_score = serializers.SerializerMethodField()

    class Meta:
        model  = UserProfile
        fields = [
            # Employment
            'employment_status',
            'employer_name',
            'job_title',
            'monthly_income',
            # Emergency contact
            'emergency_name',
            'emergency_phone',
            'emergency_relation',
            # Referees
            'referee1_name',
            'referee1_phone',
            'referee1_relation',
            'referee2_name',
            'referee2_phone',
            'referee2_relation',
            # Bio
            'bio',
            'date_of_birth',
            # Score
            'completion_score',
            'updated_at',
        ]
        read_only_fields = ['completion_score', 'updated_at']

    def get_completion_score(self, obj):
        return obj.completion_score()


class ProfileCompletionSerializer(serializers.ModelSerializer):
    """
    Breakdown of each section and its score.
    Drives the progress bar on the frontend.
    """
    completion_breakdown = serializers.SerializerMethodField()
    profile_photo_url    = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'profile_completion',
            'profile_photo_url',
            'completion_breakdown',
        ]

    def get_profile_photo_url(self, obj):
        if obj.profile_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_photo.url)
        return None

    def get_completion_breakdown(self, obj):
        # Safely get UserProfile if it exists
        try:
            profile = obj.profile
        except UserProfile.DoesNotExist:
            profile = None

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
                'points':   15,
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
                'points':   5,
            },
            'kyc_tier_2': {
                'complete': obj.kyc_tier >= 2,
                'points':   5,
            },
            'emergency_contact': {
                'complete': bool(
                    profile and
                    profile.emergency_name and
                    profile.emergency_phone
                ),
                'points': 20,
            },
            'referee_1': {
                'complete': bool(
                    profile and
                    profile.referee1_name and
                    profile.referee1_phone
                ),
                'points': 10,
            },
            'referee_2': {
                'complete': bool(
                    profile and
                    profile.referee2_name and
                    profile.referee2_phone
                ),
                'points': 5,
            },
        }


class ProfilePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['profile_photo']

    def validate_profile_photo(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                'Profile photo must be smaller than 5MB.'
            )
        allowed = ['image/jpeg', 'image/png', 'image/jpg']
        if value.content_type not in allowed:
            raise serializers.ValidationError(
                'Only JPEG and PNG images are accepted.'
            )
        return value


# ══════════════════════════════════════════════════════════════════════════
# IDENTITY VERIFICATION SERIALIZERS
# ══════════════════════════════════════════════════════════════════════════

class BVNVerificationSerializer(serializers.Serializer):
    bvn = serializers.CharField(min_length=11, max_length=11)

    def validate_bvn(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'BVN must be 11 digits, numbers only.'
            )
        return value
    

class NINVerificationSerializer(serializers.Serializer):
    nin = serializers.CharField(min_length=11, max_length=11)

    def validate_nin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'NIN must be 11 digits with no letters or spaces.'
            )
        return value


# ══════════════════════════════════════════════════════════════════════════
# KYC SERIALIZERS
# ══════════════════════════════════════════════════════════════════════════

class KYCTier1Serializer(serializers.Serializer):
    """
    Tier 1 — phone verified + NIN.
    NIN is submitted and mock-verified here.
    In production: calls Prembly API.
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
    Tier 2 — BVN + address.
    In production: calls Mono API for BVN.
    """
    bvn           = serializers.CharField(min_length=11, max_length=11)
    address_line1 = serializers.CharField(max_length=255)
    address_line2 = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
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
    Tier 3 — income proof + NOK + employment.
    NOK = Next of Kin.
    """
    employer_name    = serializers.CharField(max_length=128)
    monthly_income   = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    nok_name         = serializers.CharField(max_length=128)
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
    Current KYC state — tier, what is verified,
    and what tier the user qualifies for right now.
    """
    kyc_tier_label     = serializers.CharField(
        source='get_kyc_tier_display',
        read_only=True,
    )
    tier_qualified_for = serializers.IntegerField(
        source='get_kyc_requirements_met',
        read_only=True,
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


# ══════════════════════════════════════════════════════════════════════════
# PIN & DEVICE SERIALIZERS
# ══════════════════════════════════════════════════════════════════════════

class SetPINSerializer(serializers.Serializer):
    """
    Sets a PIN and registers the device.
    Returns a device_token the app stores locally.
    """
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
    device_name = serializers.CharField(
        max_length=128,
        required=False,
        allow_blank=True,
        default='Unknown Device',
    )
    platform    = serializers.ChoiceField(
        choices=['android', 'ios', 'web'],
        default='android',
    )

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'PIN must contain digits only.'
            )
        blocked = ['0000', '1234', '1111', '9999', '1212']
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
    """
    Login using phone + PIN + device_token.
    No password required once PIN is set.
    """
    phone        = serializers.CharField()
    pin          = serializers.CharField(
        min_length=4,
        max_length=6,
        write_only=True,
    )
    device_token = serializers.CharField()

    def validate_phone(self, value):
        if value.startswith('0'):
            value = '+234' + value[1:]
        return value


class DeviceSessionSerializer(serializers.ModelSerializer):
    """
    Read serializer — lists trusted devices
    on a user's account.
    """
    class Meta:
        model  = DeviceSession
        fields = [
            'id',
            'device_name',
            'platform',
            'is_active',
            'last_used',
            'created_at',
        ]
        read_only_fields = fields


# ══════════════════════════════════════════════════════════════════════════
# REFERRAL SERIALIZERS
# ══════════════════════════════════════════════════════════════════════════

class ReferralCreditSerializer(serializers.ModelSerializer):
    """
    One credit event — who triggered it,
    what level, how many points.
    """
    source_name = serializers.SerializerMethodField()

    class Meta:
        model  = ReferralCredit
        fields = [
            'id',
            'source_name',
            'credit_type',
            'level',
            'points',
            'description',
            'created_at',
        ]
        read_only_fields = fields

    def get_source_name(self, obj):
        return (
            f'{obj.source_user.first_name} '
            f'{obj.source_user.last_name}'
        )


class ReferralDashboardSerializer(serializers.Serializer):
    """
    Full referral summary for the dashboard screen.
    """
    referral_code    = serializers.CharField()
    referral_link    = serializers.CharField()
    total_referrals  = serializers.IntegerField()
    direct_referrals = serializers.IntegerField()
    total_points     = serializers.IntegerField()
    tree             = serializers.ListField()