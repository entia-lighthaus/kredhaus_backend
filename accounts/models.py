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
    # When we are ready to go live, we will use Prembly for NIN and Mono for BVN linkage
    # Identity verification fields
    nin             = models.CharField(max_length=11, blank=True, null=True)
    bvn             = models.CharField(max_length=11, blank=True, null=True)
    nin_verified    = models.BooleanField(default=False)
    bvn_verified    = models.BooleanField(default=False)
    phone_verified  = models.BooleanField(default=False)

    USERNAME_FIELD  = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.phone})'
    
