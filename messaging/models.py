# messaging/models.py
from django.db import models
from accounts.models import User

class Conversation(models.Model):
    CONTEXT_TYPES = [
        ('landlord',  'Landlord'),
        ('homeowner',  'Homeowner'),
        ('vendor',    'Vendor'),
        ('neighbor',  'Neighbor'),
    ]

    # The lease this conversation belongs to
    # (keeps chat scoped to a tenancy — not floating globally)
    # Landlord-tenant threads will be linked to the lease, while vendor threads will be linked via the maintenance_request FK below.
    lease = models.ForeignKey(
        'tenancy.Lease',
        on_delete=models.CASCADE,
        related_name='conversations'
    )
    participants = models.ManyToManyField(User, related_name='conversations')
    context_type = models.CharField(max_length=20, choices=CONTEXT_TYPES)

    # For vendor threads: link to the maintenance request that spawned it
    maintenance_request = models.OneToOneField(
        'tenancy.MaintenanceRequest',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conversation'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_message_at']

    # Denormalised for inbox performance — avoid N+1 on list view
    # Updated on every new message, or when a message is edited (e.g. to update the preview text)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_preview = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"{self.context_type} thread | Lease {self.lease_id}"


# ── Message ───────────────────────────────────────────────────────────────────
# Each message belongs to a conversation, and has a sender (the User who sent it).
class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(User, on_delete=models.PROTECT)
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
