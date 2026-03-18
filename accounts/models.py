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
    
    phone      = models.CharField(max_length=20, unique=True)
    email      = models.EmailField(blank=True, null=True, unique=True)
    first_name = models.CharField(max_length=64)
    last_name  = models.CharField(max_length=64)
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tenant')

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
        
