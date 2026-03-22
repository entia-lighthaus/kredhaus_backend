from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager


# Creating a Manager for the Custom User. Create this first,before defining user, else, it raises an error.
# Django's default manager expects a username field. Since we're using phone, we need to write our own. 

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


class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = [
        ('tenant', 'Tenant'),
        ('homeowner', 'Homeowner'),
        ('vendor', 'Vendor'),
        ('admin', 'Admin'),
    ]
    objects = UserManager()
    
    # Profile and its completion status
    phone      = models.CharField(max_length=20, unique=True)
    email      = models.EmailField(blank=True, null=True, unique=True)
    first_name = models.CharField(max_length=64)
    last_name  = models.CharField(max_length=64)
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tenant')
    profile_photo      = models.ImageField(
        upload_to='profile_photos/',
        null=True,
        blank=True,
    )
    profile_completion = models.PositiveSmallIntegerField(default=0) # This field will be automatically calculated based on the information the user has provided. 
    # It can be used to encourage users to complete their profiles by showing them how much of their profile is complete. i.e 0-100%


    # Emergency contact
    emergency_name     = models.CharField(max_length=128, blank=True)
    emergency_phone    = models.CharField(max_length=20, blank=True)
    emergency_relationship = models.CharField(max_length=64, blank=True)

    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)


    # NIN and BVN Information. For now, We use a dummy mocks.
    # When we are ready to go live, we will use Prembly with strong liveness check for NIN... and Mono for BVN linkage
    # Identity verification fields
    nin             = models.CharField(max_length=11, blank=True, null=True)
    bvn             = models.CharField(max_length=11, blank=True, null=True)
    nin_verified    = models.BooleanField(default=False)
    bvn_verified    = models.BooleanField(default=False)
    phone_verified  = models.BooleanField(default=False)


    # Adding KYC to the user model
    KYC_TIER_CHOICES = [
        (0, 'Unverified'),
        (1, 'Basic'),
        (2, 'Financial'),
        (3, 'Financing'),
    ]

    kyc_tier = models.IntegerField(choices=KYC_TIER_CHOICES, default=0)

    # Tier 2 fields
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    lga           = models.CharField(max_length=64, blank=True, null=True)
    state         = models.CharField(max_length=64, blank=True, null=True)

    # Tier 3 fields
    employer_name    = models.CharField(max_length=128, blank=True, null=True)
    monthly_income   = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    nok_name         = models.CharField(max_length=128, blank=True, null=True)
    nok_phone        = models.CharField(max_length=20, blank=True, null=True)
    nok_relationship = models.CharField(max_length=64, blank=True, null=True)

    USERNAME_FIELD  = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.phone})'
    
    
    # This function checks what information the user has completed during registration and returns which tier they qualify for.  
    def get_kyc_requirements_met(self):
     
        if self.nin_verified and self.phone_verified:
            if self.bvn_verified and self.address_line1:
                if self.nok_name and self.monthly_income:
                    return 3
                return 2
            return 1
        return 0

    
    # This function automatically sets kyc_tier based on what information the user has verified.
    def upgrade_kyc_tier(self):
        
        self.kyc_tier = self.get_kyc_requirements_met()
        self.save(update_fields=['kyc_tier'])


    # This function calculates the profile completion percentage based on the information the user has provided. 
    # It can be used to encourage users to complete their profiles by showing them how much of their profile is complete. i.e 0-100%
    def calculate_profile_completion(self):
        score = 0

        # Basic info — 20 points
        if self.first_name and self.last_name:
            score += 10
        if self.email:
            score += 5
        if self.profile_photo:
            score += 5

        # Verification — 30 points
        if self.phone_verified:
            score += 10
        if self.nin_verified:
            score += 10
        if self.bvn_verified:
            score += 10

        # KYC — 20 points
        if self.kyc_tier >= 1:
            score += 10
        if self.kyc_tier >= 2:
            score += 10

        # Emergency contact — 15 points
        if self.emergency_name and self.emergency_phone:
            score += 15

        # Referees — 15 points
        if self.referees.count() >= 1:
            score += 10
        if self.referees.count() >= 2:
            score += 5

        self.profile_completion = score
        self.save(update_fields=['profile_completion'])
        return score
    
    # PIN login
    # The actual fingerprint or Face ID scan happens entirely on the mobile device — iOS and Android handle that natively. 
    # What the backend handles is the PIN as a fallback and device trust scoring.
    pin_hash      = models.CharField(max_length=128, blank=True)
    pin_set       = models.BooleanField(default=False)
        

# The Referee model represents a reference provided by a user, typically for tenancy applications. 
# It includes the referee's contact information and their relationship to the user. 
# This model is linked to the User model via a ForeignKey, allowing each user to have multiple referees if needed.
class Referee(models.Model):
    user         = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='referees',
    )
    full_name    = models.CharField(max_length=128)
    phone        = models.CharField(max_length=20)
    email        = models.EmailField(blank=True)
    occupation   = models.CharField(max_length=128, blank=True)
    relationship = models.CharField(max_length=64)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.full_name} — referee for {self.user.phone}'
    

# This class handles Security access and authentication on devices
class TrustedDevice(models.Model):
    user        = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trusted_devices',
    )
    device_id   = models.CharField(max_length=255)
    device_name = models.CharField(max_length=128, blank=True)
    platform    = models.CharField(
        max_length=20,
        choices=[
            ('ios',     'iOS'),
            ('android', 'Android'),
            ('web',     'Web'),
        ],
        default='android',
    )
    is_trusted    = models.BooleanField(default=False)
    trust_score   = models.PositiveSmallIntegerField(default=0)
    last_seen     = models.DateTimeField(auto_now=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'device_id']

    def __str__(self):
        return f'{self.user.phone} — {self.device_name or self.device_id[:12]}'