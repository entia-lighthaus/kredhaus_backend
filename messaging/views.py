from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from accounts.models import User
from tenancy.models import Lease, Property, MaintenanceRequest
from .models import Conversation, Message, MessageReadReceipt
from .serializers import ConversationInboxSerializer, MessageSerializer


# ConversationCreateView is used to start a new conversation thread between two users, scoped to a lease, property, or maintenance request.
# POST /api/v1/messaging/conversations/
# Creates a new conversation thread.
class ConversationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        context_type = request.data.get('context_type') # landlord, neighbor, or vendor
        participant_id = request.data.get('participant_id') # the other user in the conversation
        other_user = get_object_or_404(User, id=participant_id)

        # Resolve scope
        lease = None
        property_obj = None
        maintenance_request = None

        if context_type == 'landlord':
            lease = get_object_or_404(
                Lease, id=request.data.get('lease_id')
            )
        elif context_type == 'neighbor':
            property_obj = get_object_or_404(
                Property, id=request.data.get('property_id')
            )
        elif context_type == 'vendor':
            maintenance_request = get_object_or_404(
                MaintenanceRequest, id=request.data.get('maintenance_request_id')
            )

        # Prevent duplicate threads
        existing = Conversation.objects.filter(
            context_type=context_type,
            participants=request.user
        ).filter(participants=other_user)

        if lease:
            existing = existing.filter(lease=lease)
        elif property_obj:
            existing = existing.filter(property=property_obj)
        elif maintenance_request:
            existing = existing.filter(maintenance_request=maintenance_request)

        if existing.first():
            return Response(
                ConversationInboxSerializer(
                    existing.first(), context={'request': request}
                ).data
            )

        # Create new conversation
        convo = Conversation.objects.create(
            context_type=context_type,
            lease=lease,
            property=property_obj,
            maintenance_request=maintenance_request,
            last_message_at=timezone.now(),
            last_message_preview=""
        )
        convo.participants.add(request.user, other_user)

        return Response(
            ConversationInboxSerializer(convo, context={'request': request}).data,
            status=201
        )
    


# MessageCreateView is used to send a message within an existing conversation thread. 
# This is the REST fallback when WebSocket isn't connected.
class MessageCreateView(CreateAPIView):
    """
    POST /api/v1/messaging/conversations/<id>/messages/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        convo = get_object_or_404(
            Conversation, pk=pk, participants=request.user
        )
        body = request.data.get('body', '').strip()
        if not body:
            return Response({'error': 'Message body is required.'}, status=400)

        msg = Message.objects.create(
            conversation=convo,
            sender=request.user,
            body=body
        )

        # Update inbox preview
        convo.last_message_at = msg.sent_at
        convo.last_message_preview = body[:120]
        convo.save(update_fields=['last_message_at', 'last_message_preview'])

        # Create unread receipts for other participants
        for participant in convo.participants.exclude(id=request.user.id):
            MessageReadReceipt.objects.create(message=msg, user=participant)

        return Response(MessageSerializer(msg, context={'request': request}).data, status=201)
    



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
