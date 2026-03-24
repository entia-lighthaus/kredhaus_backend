from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from .models import Conversation, Message, MessageReadReceipt
from .serializers import ConversationInboxSerializer, MessageSerializer



class InboxView(ListAPIView):
    """
    GET /api/messaging/inbox/?lease_id=<id>
    Returns the conversation list you see on the Chat tab.
    Only conversations for the specified lease are returned, and only those that the user is a participant in.
    """
    serializer_class = ConversationInboxSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        lease_id = self.request.query_params.get('lease_id')
        user = self.request.user
        return (
            Conversation.objects
            .filter(lease_id=lease_id, participants=user)
            .annotate(
                unread_count=Count(
                    'messages',
                    filter=Q(
                        messages__receipts__user=user,
                        messages__receipts__read_at__isnull=True
                    )
                )
            )
            .order_by('-last_message_at')
        )


# ConversationDetailView returns the conversation metadata along with the first page of messages for that conversation.
class ConversationDetailView(RetrieveAPIView):
    """
    GET /api/messaging/conversations/<id>/
    Returns metadata + first page of messages.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        convo = get_object_or_404(
            Conversation, pk=pk, participants=request.user
        )

        messages = convo.messages.order_by('-sent_at')[:50]

        # Mark all as read
        MessageReadReceipt.objects.filter(
            message__conversation=convo,
            user=request.user,
            read_at__isnull=True
        ).update(read_at=timezone.now())

        return Response({
            "conversation": ConversationInboxSerializer(
                convo,
                context={'request': request}  # ← this is the fix
            ).data,
            "messages": MessageSerializer(
                reversed(list(messages)),
                many=True,
                context={'request': request}  # ← and here
            ).data
        })


# This view supports paginated loading of older messages when you scroll up in the chat history.
class MessageHistoryView(ListAPIView):
    """
    GET /api/messaging/conversations/<id>/messages/?cursor=<timestamp>
    Paginated older message loading.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        convo_id = self.kwargs['pk']
        cursor = self.request.query_params.get('cursor')
        qs = Message.objects.filter(
            conversation_id=convo_id,
            conversation__participants=self.request.user
        ).order_by('-sent_at')
        if cursor:
            qs = qs.filter(sent_at__lt=cursor)
        return qs[:30]
