from rest_framework import serializers
from django.utils import timezone
from .models import Conversation, Message, MessageReadReceipt
from accounts.serializers import UserBriefSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender = UserBriefSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender', 'body', 'sent_at', 'is_mine', 'is_read']

    def get_is_mine(self, obj):
        request = self.context.get('request')
        return request and obj.sender_id == request.user.id

    def get_is_read(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        receipt = obj.receipts.filter(user=request.user).first()
        return receipt.read_at is not None if receipt else False


class ConversationInboxSerializer(serializers.ModelSerializer):
    """
    Powers the Chat tab inbox list.
    Returns one row per conversation with avatar, name, badge, preview.
    """
    contact = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True)  # annotated in view
    last_message_at = serializers.DateTimeField(format="%b %d, %I:%M %p")

    class Meta:
        model = Conversation
        fields = [
            'id',
            'context_type',   # 'landlord' | 'vendor' | 'neighbor'
            'contact',
            'last_message_preview',
            'last_message_at',
            'unread_count',
        ]



    def get_contact(self, obj):
        request = self.context.get('request')
        other = obj.participants.exclude(id=request.user.id).first()
        if not other:
            return None
        return {
            'id': other.id,
            'name': f"{other.first_name} {other.last_name}".strip(),  # ← fix here
            'avatar_url': None,
            'role_label': self._role_label(obj, other),
        }



    def _role_label(self, conversation, user):
        if conversation.context_type == 'landlord':
            return 'Landlord'
        elif conversation.context_type == 'vendor':
            # e.g. "ABC Plumbing Services" — pull from vendor profile
            profile = getattr(user, 'vendor_profile', None)
            return profile.business_name if profile else 'Vendor'
        elif conversation.context_type == 'neighbor':
            # e.g. "Sarah (Apt 3B)"
            profile = getattr(user, 'tenant_profile', None)
            unit = profile.unit_label if profile else ''
            return f"Neighbor · {unit}" if unit else 'Neighbor'
        return user.get_role_display()


class ConversationDetailSerializer(serializers.ModelSerializer):
    """
    Powers the open conversation view (full thread).
    """
    contact = ConversationInboxSerializer.get_contact  # reuse
    messages = MessageSerializer(many=True, read_only=True)
    participants = UserBriefSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'context_type', 'participants', 'messages', 'created_at']