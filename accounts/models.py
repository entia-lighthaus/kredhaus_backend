from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager


# ── Manager ────────────────────────────────────────────────────────────────

class UserManager(BaseUserManager):

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Phone number is required')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone, password, **extra_fields)


# ── User ───────────────────────────────────────────────────────────────────

class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = [
        ('tenant',    'Tenant'),
        ('homeowner',     'Homeowner'),
        ('vendor',    'Vendor'),
        ('admin',     'Admin'),
    ]

    KYC_TIER_CHOICES = [
        (0, 'Unverified'),
        (1, 'Basic'),
        (2, 'Financial'),
        (3, 'Financing'),
    ]

    objects = UserManager()

    # ── Core identity ──────────────────────────────────────────────────
    phone       = models.CharField(max_length=20, unique=True)
    email       = models.EmailField(blank=True, null=True, unique=True)
    first_name  = models.CharField(max_length=64)
    last_name   = models.CharField(max_length=64)
    role        = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='tenant',
    )
    date_joined = models.DateTimeField(default=timezone.now)
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)

    # ── Profile ────────────────────────────────────────────────────────
    profile_photo      = models.ImageField(
        upload_to='profile_photos/',
        null=True,
        blank=True,
    )
    profile_completion = models.PositiveSmallIntegerField(default=0)

    # ── PIN login ──────────────────────────────────────────────────────
    pin_hash = models.CharField(max_length=128, blank=True)
    pin_set  = models.BooleanField(default=False)

    # ── Referral tree ──────────────────────────────────────────────────
    referral_code = models.CharField(max_length=12, unique=True, blank=True)
    referred_by   = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='direct_referrals',
    )
    referral_path = models.TextField(
        blank=True,
        help_text='Pipe-separated chain of ancestor user IDs. e.g. 1|4|7',
    )

    # ── Identity verification ──────────────────────────────────────────
    nin            = models.CharField(max_length=11, blank=True, null=True)
    bvn            = models.CharField(max_length=11, blank=True, null=True)
    nin_verified   = models.BooleanField(default=False)
    bvn_verified   = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    # ── KYC tier ───────────────────────────────────────────────────────
    kyc_tier = models.IntegerField(choices=KYC_TIER_CHOICES, default=0)

    # Tier 2
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    lga           = models.CharField(max_length=64, blank=True, null=True)
    state         = models.CharField(max_length=64, blank=True, null=True)

    # Tier 3
    employer_name    = models.CharField(max_length=128, blank=True, null=True)
    monthly_income   = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )
    nok_name         = models.CharField(max_length=128, blank=True, null=True)
    nok_phone        = models.CharField(max_length=20, blank=True, null=True)
    nok_relationship = models.CharField(max_length=64, blank=True, null=True)

    # ── Django auth config ─────────────────────────────────────────────
    USERNAME_FIELD  = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.phone})'

    # ── save ───────────────────────────────────────────────────────────
    def save(self, *args, **kwargs):
        if not self.referral_code:
            import random, string
            while True:
                code = 'KH' + ''.join(
                    random.choices(
                        string.ascii_uppercase + string.digits, k=8
                    )
                )
                if not User.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    break
        super().save(*args, **kwargs)

    # ── KYC methods ────────────────────────────────────────────────────
    def get_kyc_requirements_met(self):

        if self.nin_verified and self.phone_verified:
            if self.bvn_verified and self.address_line1:
                if self.nok_name and self.monthly_income:
                    return 3
                return 2
            return 1
        return 0


    def upgrade_kyc_tier(self):

        self.kyc_tier = self.get_kyc_requirements_met()
        self.save(update_fields=['kyc_tier'])

    # ── Referral methods ───────────────────────────────────────────────
    def build_referral_path(self):
        path  = []
        node  = self.referred_by
        depth = 0
        while node is not None and depth < 5:
            path.append(str(node.id))
            node  = node.referred_by
            depth += 1
        self.referral_path = '|'.join(path)
        self.save(update_fields=['referral_path'])


# ── UserProfile ────────────────────────────────────────────────────────────

class UserProfile(models.Model):

    EMPLOYMENT_STATUS_CHOICES = [
        ('employed',      'Employed'),
        ('self_employed', 'Self Employed'),
        ('student',       'Student'),
        ('unemployed',    'Unemployed'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )

    # Employment
    # Note: employer_name and monthly_income live on User (KYC Tier 3)
    # UserProfile stores the richer employment context
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        blank=True,
    )
    job_title = models.CharField(max_length=128, blank=True)

    # Emergency contact
    emergency_name     = models.CharField(max_length=128, blank=True)
    emergency_phone    = models.CharField(max_length=20, blank=True)
    emergency_relation = models.CharField(max_length=64, blank=True)

    # Referees
    referee1_name     = models.CharField(max_length=128, blank=True)
    referee1_phone    = models.CharField(max_length=20, blank=True)
    referee1_relation = models.CharField(max_length=64, blank=True)

    referee2_name     = models.CharField(max_length=128, blank=True)
    referee2_phone    = models.CharField(max_length=20, blank=True)
    referee2_relation = models.CharField(max_length=64, blank=True)

    # Bio
    bio           = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile — {self.user.phone}'

    def completion_score(self):
        score = 0

        # Photo — 15 points
        if self.user.profile_photo:
            score += 15

        # Employment — 25 points
        if self.employment_status:
            score += 10
        if self.user.employer_name:       # reads from User
            score += 8
        if self.user.monthly_income:      # reads from User
            score += 7

        # Emergency contact — 20 points
        if self.emergency_name and self.emergency_phone:
            score += 20

        # Referees — 20 points
        if self.referee1_name and self.referee1_phone:
            score += 10
        if self.referee2_name and self.referee2_phone:
            score += 10

        # Bio and DOB — 10 points
        if self.bio:
            score += 5
        if self.date_of_birth:
            score += 5

        # KYC — 10 points
        if self.user.kyc_tier >= 1:
            score += 5
        if self.user.kyc_tier >= 2:
            score += 5

        return min(score, 100)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        score = self.completion_score()
        if self.user.profile_completion != score:
            self.user.profile_completion = score
            self.user.save(update_fields=['profile_completion'])


# ── ReferralCredit ─────────────────────────────────────────────────────────

class ReferralCredit(models.Model):

    CREDIT_TYPE_CHOICES = [
        ('signup',  'New User Signup'),
        ('kyc',     'Referral Completed KYC'),
        ('payment', 'Referral Made First Payment'),
    ]

    beneficiary = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='referral_credits',
    )
    source_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='credit_events_generated',
    )
    credit_type = models.CharField(max_length=20, choices=CREDIT_TYPE_CHOICES)
    level       = models.PositiveSmallIntegerField(
        help_text='1 = direct referral, 2 = referral of referral, etc.'
    )
    points      = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'{self.beneficiary.phone} earned {self.points} pts '
            f'(Level {self.level}) from {self.source_user.phone}'
        )


# ── DeviceSession ──────────────────────────────────────────────────────────

class DeviceSession(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='devices',
    )
    device_token = models.CharField(max_length=128, unique=True)
    device_name  = models.CharField(max_length=128, blank=True)
    platform     = models.CharField(
        max_length=20,

        choices=[
            
            ('android', 'Android'),
            ('ios',     'iOS'),
            ('web',     'Web'),
        ],
        default='android',
    )
    is_active  = models.BooleanField(default=True)
    last_used  = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-last_used']

    def __str__(self):
        return (
            f'{self.user.phone} — '
            f'{self.device_name or self.device_token[:12]}'
        )