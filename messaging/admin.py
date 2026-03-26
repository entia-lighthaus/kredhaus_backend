from django.contrib import admin
from .models import Conversation, Message, MessageReadReceipt


# The ConversationAdmin, MessageAdmin, and MessageReadReceiptAdmin classes define how the Conversation, Message, and MessageReadReceipt models are displayed and managed in the Django admin interface.
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'context_type', 'lease', 'get_participants', 'last_message_at', 'last_message_preview']
    list_filter = ['context_type']

    def get_participants(self, obj):
        return " | ".join([
            f"{u.first_name} {u.last_name} (id:{u.id})" 
            for u in obj.participants.all()
        ])
    get_participants.short_description = 'Participants'



# The MessageAdmin and MessageReadReceiptAdmin classes define how the Message and MessageReadReceipt models are displayed and managed in the Django admin interface. 
# They include list displays and search fields to facilitate easy management of messages and read receipts.
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'body', 'sent_at']
    search_fields = ['body', 'sender__first_name']

@admin.register(MessageReadReceipt)
class MessageReadReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'message', 'user', 'read_at']