from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from tenancy.models import Unit
from .models import Utility, UtilityAccount, UtilityBill
from .serializers import UtilitySerializer, UtilityAccountSerializer, UtilityBillSerializer
from .permissions import CanManageUtilityAccounts


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
        ).distinct()
        
        # Get units where user is owner
        owner_units = Unit.objects.filter(property__owner=user)
        
        # Combine and get accounts
        units = tenant_units | owner_units
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
