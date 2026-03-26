# messaging/models.py
from django.db import models
from accounts.models import User


class Conversation(models.Model):
    CONTEXT_TYPES = [
        ('landlord',  'Landlord'),
        ('homeowner',  'Homeowner'),
        ('vendor',    'Vendor'),
        ('neighbor',  'Neighbor'),
        ('supplier',  'Supplier'),  # New: for gas/water supplier chats
    ]


    # Tenant ↔ Landlord: scoped to a lease
    # Note: This is now optional, since some conversations (e.g. Tenant ↔ Neighbor) won't have a lease context.
    lease = models.ForeignKey(
        'tenancy.Lease',
        on_delete=models.CASCADE,
        null=True, blank=True,         # ← now optional
        related_name='conversations'
    )


    # Tenant ↔ Neighbor: scoped to a property
    # Note: This is now optional, since some conversations (e.g. Tenant ↔ Landlord) won't have a property context.
    property = models.ForeignKey(
        'tenancy.Property',
        on_delete=models.CASCADE,
        null=True, blank=True,         # ← new
        related_name='conversations'
    )


    # Tenant ↔ Vendor: scoped to a maintenance request
    maintenance_request = models.OneToOneField(
        'tenancy.MaintenanceRequest',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conversation'
    )

    # Tenant ↔ Supplier: scoped to a supplier service request
    supplier_service_request = models.OneToOneField(
        'utilities.SupplierServiceRequest',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conversation'
    )

    context_type = models.CharField(max_length=20, choices=CONTEXT_TYPES)
    participants = models.ManyToManyField(
        'accounts.User',
        related_name='conversations'
    )

    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_preview = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_message_at']

    def clean(self):
        # Enforce: at least one scope must be set
        from django.core.exceptions import ValidationError
        if not any([self.lease, self.property, self.maintenance_request]):
            raise ValidationError(
                'A conversation must be scoped to a lease, property, or maintenance request.'
            )


# ── Message ───────────────────────────────────────────────────────────────────
# Each message belongs to a conversation, and has a sender (the User who sent it).
class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    sender_type = models.CharField(
        max_length=20,
        choices=[
            ('user',    'User'),
            ('supplier', 'Supplier'),
        ],
        default='user'
    )
    sender_name = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['sent_at']



# This model tracks which users have read which messages, enabling accurate unread counts and "seen" indicators in the UI.
class MessageReadReceipt(models.Model):
    """Drives the unread badge counts (e.g. '2 new' on ABC Plumbing)"""
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='receipts'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('message', 'user')
