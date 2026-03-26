from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
from messaging.models import Conversation, Message
import logging

from tenancy.models import Unit
from .models import (
    Utility, UtilityAccount, UtilityBill,
    UtilityRate, UtilityMeterProvider, UtilityMeterReading, UtilityUsageRecord,
    Supplier, SupplierService, SupplierAvailability, SupplierServiceRequest,
    SupplierMessage, SupplierRating
)
from .serializers import (
    UtilitySerializer, UtilityAccountSerializer, UtilityBillSerializer,
    UtilityRateSerializer, UtilityMeterProviderSerializer,
    UtilityMeterReadingSerializer, UtilityUsageRecordSerializer,
    SupplierListSerializer, SupplierDetailSerializer, SupplierServiceRequestSerializer,
    SupplierMessageSerializer, SupplierRatingSerializer
)
from .permissions import CanManageUtilityAccounts
from .services import process_meter_reading, confirm_meter_reading, validate_meter_reading

logger = logging.getLogger(__name__)


class UtilityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for utilities (Electricity, Gas, Water, Internet).
    Users can view available utilities for selection.
    """
    queryset = Utility.objects.filter(is_active=True)
    serializer_class = UtilitySerializer
    permission_classes = [IsAuthenticated]


class UtilityAccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage utility accounts for a specific unit.
    
    Endpoints:
    - GET /api/utilities/accounts/ - List all accounts user has access to
    - GET /api/utilities/accounts/{id}/ - Get single account
    - POST /api/utilities/accounts/ - Create new utility account
    - PUT /api/utilities/accounts/{id}/ - Update account
    - DELETE /api/utilities/accounts/{id}/ - Remove account
    - GET /api/utilities/accounts/{id}/bills/ - Get bills for account
    """
    serializer_class = UtilityAccountSerializer
    permission_classes = [IsAuthenticated, CanManageUtilityAccounts]

    def get_queryset(self):
        """Return only accounts for units the user can access."""
        user = self.request.user
        
        # Get units where user is tenant
        tenant_units = Unit.objects.filter(
            leases__tenant=user,
            leases__status__in=['active', 'pending']
        )
        
        # Get units where user is owner
        owner_units = Unit.objects.filter(property__owner=user)
        
        # Combine and deduplicate
        units = (tenant_units | owner_units).distinct()
        return UtilityAccount.objects.filter(unit__in=units)

    def perform_create(self, serializer):
        """Set connected_by field when creating account."""
        serializer.save(
            connected_by=f"{self.request.user.first_name} {self.request.user.last_name}".strip()
        )

    def perform_update(self, serializer):
        """Set last_updated_by field when updating account."""
        serializer.save(
            last_updated_by=f"{self.request.user.first_name} {self.request.user.last_name}".strip()
        )

    @action(detail=True, methods=['get'])
    def bills(self, request, pk=None):
        """
        Get all bills for a specific utility account.
        GET /api/utilities/accounts/{id}/bills/
        """
        account = self.get_object()
        bills = account.bills.all()
        serializer = UtilityBillSerializer(bills, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_unit(self, request):
        """
        Get all utility accounts for a specific unit.
        GET /api/utilities/accounts/by_unit/?unit_id={unit_id}
        """
        unit_id = request.query_params.get('unit_id')
        if not unit_id:
            return Response(
                {'error': 'unit_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        unit = get_object_or_404(Unit, id=unit_id)
        
        # Check permission
        if unit.property.owner != request.user and not unit.leases.filter(
            tenant=request.user,
            status__in=['active', 'pending']
        ).exists():
            return Response(
                {'error': 'You do not have access to this unit'},
                status=status.HTTP_403_FORBIDDEN
            )

        accounts = UtilityAccount.objects.filter(unit=unit)
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_bill_paid(self, request, pk=None):
        """
        Mark a specific bill as paid.
        POST /api/utilities/accounts/{id}/mark_bill_paid/?bill_id={bill_id}
        """
        account = self.get_object()
        bill_id = request.query_params.get('bill_id')
        
        if not bill_id:
            return Response(
                {'error': 'bill_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        bill = get_object_or_404(UtilityBill, id=bill_id, account=account)
        bill.status = 'paid'
        bill.paid_date = timezone.now().date()
        bill.save()

        return Response(
            {'message': 'Bill marked as paid', 'bill': UtilityBillSerializer(bill).data}
        )

    @action(detail=True, methods=['post'])
    def submit_meter_reading(self, request, pk=None):
        """
        Submit a manual meter reading for the account.
        POST /api/utilities/accounts/{id}/submit_meter_reading/
        
        {
            "previous_reading": 100,
            "current_reading": 145,
            "reading_date": "2026-03-26",
            "notes": "March meter reading"
        }
        
        OR for direct consumption:
        {
            "consumption": 45,
            "reading_date": "2026-03-26"
        }
        """
        account = self.get_object()
        reading_date = request.data.get('reading_date')
        
        # Check if reading already exists for this date
        existing_reading = UtilityMeterReading.objects.filter(
            account=account,
            reading_date=reading_date,
            source='manual'
        ).first()
        
        # Create meter reading data
        data = request.data.copy()
        data['account_id'] = account.id
        data['source'] = 'manual'
        data['submitted_by'] = f"{request.user.first_name} {request.user.last_name}".strip()
        
        if existing_reading:
            # Update existing reading
            serializer = UtilityMeterReadingSerializer(existing_reading, data=data, partial=True)
            status_code = status.HTTP_200_OK
            is_update = True
        else:
            # Create new reading
            serializer = UtilityMeterReadingSerializer(data=data)
            status_code = status.HTTP_201_CREATED
            is_update = False
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        meter_reading = serializer.save()
        
        # Validate reading
        is_valid, errors = validate_meter_reading(meter_reading)
        if not is_valid:
            if not is_update:
                meter_reading.delete()
            return Response(
                {'errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Return preview with estimated bill
        response_data = UtilityMeterReadingSerializer(meter_reading).data
        if is_update:
            response_data['message'] = 'Meter reading updated successfully'
        
        return Response(response_data, status=status_code)

    @action(detail=True, methods=['post'])
    def confirm_meter_reading(self, request, pk=None):
        """
        Confirm a manual meter reading and lock it in.
        POST /api/utilities/accounts/{id}/confirm_meter_reading/?reading_id={reading_id}
        """
        account = self.get_object()
        reading_id = request.query_params.get('reading_id')
        
        if not reading_id:
            return Response(
                {'error': 'reading_id query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        meter_reading = get_object_or_404(
            UtilityMeterReading,
            id=reading_id,
            account=account,
            source='manual'
        )
        
        try:
            usage_record = confirm_meter_reading(meter_reading)
            return Response({
                'message': 'Meter reading confirmed',
                'usage_record': UtilityUsageRecordSerializer(usage_record).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def consumption_history(self, request, pk=None):
        """
        Get consumption history for the account.
        GET /api/utilities/accounts/{id}/consumption_history/
        ?days=90 (default 90 days)
        """
        account = self.get_object()
        days = int(request.query_params.get('days', 90))
        
        from datetime import timedelta
        start_date = timezone.now().date() - timedelta(days=days)
        
        usage_records = account.usage_records.filter(
            period_end__gte=start_date
        ).order_by('-period_end')
        
        serializer = UtilityUsageRecordSerializer(usage_records, many=True)
        return Response(serializer.data)


class UtilityRateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for utility rates.
    Admins manage rates through Django admin.
    """
    queryset = UtilityRate.objects.filter(is_active=True)
    serializer_class = UtilityRateSerializer
    permission_classes = [IsAuthenticated]


class UtilityBillViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for utility bills.
    Bills are managed through UtilityAccount endpoints.
    """
    serializer_class = UtilityBillSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only bills for accounts the user can access."""
        user = self.request.user
        
        # Get units where user is tenant
        tenant_units = Unit.objects.filter(
            leases__tenant=user,
            leases__status__in=['active', 'pending']
        ).distinct()
        
        # Get units where user is owner
        owner_units = Unit.objects.filter(property__owner=user)
        
        # Combine and get bills
        units = tenant_units | owner_units
        accounts = UtilityAccount.objects.filter(unit__in=units)
        return UtilityBill.objects.filter(account__in=accounts)


# ── Webhook for Smart Meter Data ────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def webhook_meter_reading(request):
    """
    Webhook endpoint to receive smart meter data from external providers.
    POST /api/utilities/webhooks/meter-reading/
    
    Expected payload:
    {
        "account_number": "ELEC-123456",
        "current_reading": 145,
        "previous_reading": 100,
        "reading_timestamp": "2026-03-26T10:30:00Z",
        "webhook_token": "token_for_verification"
    }
    
    Returns:
    {
        "status": "success",
        "reading_id": 123,
        "consumption": 45,
        "estimated_bill": {...}
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    try:
        # Get account
        account = UtilityAccount.objects.get(
            account_number=data.get('account_number')
        )
        
        # Verify webhook token if provided
        if hasattr(account, 'meter_provider') and account.meter_provider.webhook_token:
            provided_token = data.get('webhook_token')
            if provided_token != account.meter_provider.webhook_token:
                logger.warning(f"Invalid webhook token for account {account.id}")
                return JsonResponse(
                    {'error': 'Invalid webhook token'},
                    status=401
                )
        
        # Parse reading date
        from datetime import datetime
        reading_datetime = datetime.fromisoformat(
            data.get('reading_timestamp', timezone.now().isoformat())
        )
        reading_date = reading_datetime.date()
        
        # Prevent duplicate daily readings by updating existing same-day record.
        meter_reading, created = UtilityMeterReading.objects.update_or_create(
            account=account,
            reading_date=reading_date,
            defaults={
                'current_reading': data.get('current_reading'),
                'previous_reading': data.get('previous_reading'),
                'source': 'smart_meter',
                'submitted_by': data.get('provider_name', 'Smart Meter API'),
                'is_confirmed': True,
                'notes': data.get('notes', ''),
            }
        )

        # Process the reading
        usage_record = process_meter_reading(meter_reading)
        
        if not usage_record:
            raise ValueError("Failed to process meter reading")
        
        # Update meter provider
        account.meter_provider.last_reading_date = reading_date
        account.meter_provider.last_sync_attempt = timezone.now()
        account.meter_provider.save()
        
        logger.info(
            f"Processed smart meter reading for account {account.id}: "
            f"{meter_reading.calculated_consumption} units"
        )
        
        return JsonResponse({
            'status': 'success',
            'reading_id': meter_reading.id,
            'consumption': float(meter_reading.calculated_consumption),
            'estimated_bill': usage_record.cost_breakdown
        })
    
    except UtilityAccount.DoesNotExist:
        logger.warning(f"Account not found: {data.get('account_number')}")
        return JsonResponse({'error': 'Account not found'}, status=404)
    
    except ValueError as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return JsonResponse(
            {'error': str(e)},
            status=400
        )

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return JsonResponse(
            {'error': 'Internal server error'},
            status=500
        )


@api_view(['GET'])
def meter_reading_list(request, account_id):
    """
    Get all meter readings for an account.
    GET /api/utilities/accounts/{account_id}/meter-readings/
    """
    account = get_object_or_404(UtilityAccount, id=account_id)
    
    # Check permission
    user = request.user
    if account.unit.property.owner != user and not account.unit.leases.filter(
        tenant=user,
        status__in=['active', 'pending']
    ).exists():
        return Response(
            {'error': 'You do not have access to this account'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    readings = account.meter_readings.all()
    serializer = UtilityMeterReadingSerializer(readings, many=True)
    return Response(serializer.data)


# ── Supplier ViewSets ──────────────────────────────────────────────────────

class SupplierViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve gas/water suppliers.
    
    Endpoints:
    - GET /api/v1/suppliers/ - List suppliers (optionally filtered by utility_type)
    - GET /api/v1/suppliers/{id}/ - Get supplier detail with services and ratings
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter suppliers by utility type if provided."""
        queryset = Supplier.objects.filter(is_available=True, status='active')
        
        utility_type = self.request.query_params.get('utility_type')
        if utility_type:
            queryset = queryset.filter(utility__name=utility_type)
        
        return queryset
    
    def get_serializer_class(self):
        """Use summary serializer for list, detail for retrieve."""
        if self.action == 'retrieve':
            return SupplierDetailSerializer
        return SupplierListSerializer


class SupplierServiceRequestViewSet(viewsets.ModelViewSet):
    """
    Manage tenant's service requests to suppliers.
    
    Endpoints:
    - GET /api/v1/service-requests/ - List user's requests
    - POST /api/v1/service-requests/ - Create new request
    - GET /api/v1/service-requests/{id}/ - Get request detail with messages
    - PATCH /api/v1/service-requests/{id}/ - Update request status
    - POST /api/v1/service-requests/{id}/messages/ - Send message
    """
    serializer_class = SupplierServiceRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return only requests for units the user can access."""
        user = self.request.user
        
        # Get units where user is tenant
        tenant_units = Unit.objects.filter(
            leases__tenant=user,
            leases__status__in=['active', 'pending']
        )
        
        # Get units where user is owner
        owner_units = Unit.objects.filter(property__owner=user)
        
        # Combine and get requests
        units = (tenant_units | owner_units).distinct()
        return SupplierServiceRequest.objects.filter(unit__in=units)
    
    def perform_create(self, serializer):
        """Validate and save new service request."""
        supplier_id = serializer.validated_data.get('supplier_id')
        service_id = serializer.validated_data.get('service_id')
        unit_id = serializer.validated_data.get('unit_id')
        
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            service = SupplierService.objects.get(id=service_id, supplier=supplier)
            unit = Unit.objects.get(id=unit_id)
        except (Supplier.DoesNotExist, SupplierService.DoesNotExist, Unit.DoesNotExist):
            raise serializers.ValidationError("Invalid supplier, service, or unit")
        
        # Calculate total
        quantity = serializer.validated_data.get('quantity', 1)
        service_price = service.price * quantity
        delivery_fee = supplier.delivery_fee if serializer.validated_data.get('request_type') == 'delivery' else 0
        total_amount = service_price + delivery_fee
        
        service_request = serializer.save(
            supplier=supplier,
            service=service,
            unit=unit,
            service_price=service_price,
            delivery_fee=delivery_fee,
            total_amount=total_amount,
            created_by=f"{self.request.user.first_name} {self.request.user.last_name}".strip()
        )
        
        # Create conversation for chat
        conversation = Conversation.objects.create(
            context_type='supplier',
            supplier_service_request=service_request,
            last_message_at=timezone.now(),
            last_message_preview="Service request created"
        )
        conversation.participants.add(self.request.user)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """
        Send a message in the supplier chat.
        POST /api/v1/service-requests/{id}/send_message/
        
        {
            "message_text": "Can you come by 3pm?",
            "sender_name": "John Tenant"
        }
        """
        service_request = self.get_object()
        
        data = request.data.copy()
        data['service_request'] = service_request.id
        data['sender_type'] = 'tenant'
        data['sender_name'] = f"{request.user.first_name} {request.user.last_name}".strip()
        
        serializer = SupplierMessageSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        supplier_message = serializer.save()
        
        # Also create message in conversation
        conversation = service_request.conversation
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            sender_type='user',
            sender_name=data['sender_name'],
            body=supplier_message.message_text
        )
        
        # Update conversation last message
        conversation.last_message_at = timezone.now()
        conversation.last_message_preview = supplier_message.message_text[:120]
        conversation.save()
        
        # Return all messages for this request
        messages = service_request.messages.all()
        message_serializer = SupplierMessageSerializer(messages, many=True)
        return Response(message_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Get all messages for a service request.
        GET /api/v1/service-requests/{id}/messages/
        """
        service_request = self.get_object()
        messages = service_request.messages.all()
        serializer = SupplierMessageSerializer(messages, many=True)
        return Response(serializer.data)


class SupplierRatingViewSet(viewsets.ModelViewSet):
    """
    Create and view supplier ratings.
    
    Endpoints:
    - POST /api/v1/supplier-ratings/ - Create rating (must have completed service request)
    - GET /api/v1/supplier-ratings/ - List supplier ratings
    """
    serializer_class = SupplierRatingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get ratings for a specific supplier."""
        supplier_id = self.request.query_params.get('supplier_id')
        if supplier_id:
            return SupplierRating.objects.filter(supplier_id=supplier_id)
        return SupplierRating.objects.all()
    
    def perform_create(self, serializer):
        """Validate service request is completed before rating."""
        service_request_id = self.request.data.get('service_request')
        
        try:
            service_request = SupplierServiceRequest.objects.get(id=service_request_id)
            if service_request.status != 'completed':
                raise serializers.ValidationError("Can only rate completed requests")
        except SupplierServiceRequest.DoesNotExist:
            raise serializers.ValidationError("Service request not found")
        
        unit = service_request.unit
        reviewer_name = f"{self.request.user.first_name} {self.request.user.last_name}".strip()
        
        serializer.save(
            supplier=service_request.supplier,
            service_request=service_request,
            unit=unit,
            reviewer_name=reviewer_name
        )

