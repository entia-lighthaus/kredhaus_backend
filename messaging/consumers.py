import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Message, MessageReadReceipt
from accounts.models import User


# ChatConsumer handles the WebSocket connection for a single conversation thread.
# It verifies the user is authenticated and a participant in the conversation, then listens for incoming messages and broadcasts them to all participants in real-time.
class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group = f"chat_{self.conversation_id}"
        self.user = self.scope['user']

        # Auth check
        if not self.user.is_authenticated:
            await self.close()
            return

        # Verify user is a participant
        is_member = await self.is_participant()
        if not is_member:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        body = data.get('body', '').strip()
        if not body:
            return

        # Save to DB
        message = await self.save_message(body)

        # Broadcast to all participants in this room
        await self.channel_layer.group_send(
            self.room_group,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'sender_id': self.user.id,
                'sender_name': self.user.full_name,
                'body': body,
                'sent_at': message.sent_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def is_participant(self):
        return Conversation.objects.filter(
            id=self.conversation_id,
            participants=self.user
        ).exists()

    @database_sync_to_async
    def save_message(self, body):
        convo = Conversation.objects.get(id=self.conversation_id)
        msg = Message.objects.create(
            conversation=convo, sender=self.user, body=body
        )
        # Update inbox preview
        convo.last_message_at = msg.sent_at
        convo.last_message_preview = body[:120]
        convo.save(update_fields=['last_message_at', 'last_message_preview'])

        # Create unread receipts for all OTHER participants
        for participant in convo.participants.exclude(id=self.user.id):
            MessageReadReceipt.objects.create(message=msg, user=participant)

        return msg