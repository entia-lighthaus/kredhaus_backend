from django.shortcuts import render
from rest_framework          import status
from rest_framework.views    import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils            import timezone

from .models import Property, Unit, Lease, RentPayment, MaintenanceRequest
from .serializers import (
    PropertySerializer,
    UnitSerializer,
    UnitTenantSerializer,
    LeaseOwnerSerializer,
    LeaseTenantSerializer,
    LeaseCreateSerializer,
    RentPaymentSerializer,
    RentPaymentCreateSerializer,
    MaintenanceRequestSerializer,
    MaintenanceRequestCreateSerializer,
    MaintenanceStatusUpdateSerializer,
)


# ── Helper ─────────────────────────────────────────────────────────────────

def is_owner(user):
    return user.role == 'homeowner'

def is_tenant(user):
    return user.role == 'tenant'


# ══════════════════════════════════════════════════════════════════════════
# PROPERTY VIEWS — Owner only
# ══════════════════════════════════════════════════════════════════════════

class PropertyListCreateView(APIView):
    """
    GET  — Owner lists all their properties
    POST — Owner creates a new property
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_owner(request.user):
            return Response(
                {'error': 'Only owners can view properties.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        properties = Property.objects.filter(owner=request.user)
        serializer = PropertySerializer(properties, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not is_owner(request.user):
            return Response(
                {'error': 'Only owners can create properties.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = PropertySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# The PropertyDetailView handles retrieving, updating, and deleting a specific property instance.
class PropertyDetailView(APIView):
    """
    GET   — Owner views a single property
    PATCH — Owner updates property details
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Property.objects.get(pk=pk, owner=user)
        except Property.DoesNotExist:
            return None

    def get(self, request, pk):
        if not is_owner(request.user):
            return Response(
                {'error': 'Only owners can view property details.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        prop = self.get_object(pk, request.user)
        if not prop:
            return Response(
                {'error': 'Property not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PropertySerializer(prop)
        return Response(serializer.data)

    def patch(self, request, pk):
        if not is_owner(request.user):
            return Response(
                {'error': 'Only owners can update properties.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        prop = self.get_object(pk, request.user)
        if not prop:
            return Response(
                {'error': 'Property not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PropertySerializer(prop, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# ══════════════════════════════════════════════════════════════════════════
# UNIT VIEWS — Owner manages, Tenant views their own
# ══════════════════════════════════════════════════════════════════════════

# The UnitListCreateView allows property owners to list all units within a specific property and add new units to that property. 
# Tenants do not have access to this view, as they can only see the unit they are currently renting through their lease details.
class UnitListCreateView(APIView):
    """
    GET  — Owner lists all units in a property
    POST — Owner adds a unit to a property
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, property_pk):
        if not is_owner(request.user):
            return Response(
                {'error': 'Only owners can manage units.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            prop = Property.objects.get(pk=property_pk, owner=request.user)
        except Property.DoesNotExist:
            return Response(
                {'error': 'Property not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        units      = prop.units.all()
        serializer = UnitSerializer(units, many=True)
        return Response(serializer.data)

    def post(self, request, property_pk):
        if not is_owner(request.user):
            return Response(
                {'error': 'Only owners can add units.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            prop = Property.objects.get(pk=property_pk, owner=request.user)
        except Property.DoesNotExist:
            return Response(
                {'error': 'Property not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UnitSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(property=prop)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )



# ══════════════════════════════════════════════════════════════════════════
# LEASE VIEWS
# ══════════════════════════════════════════════════════════════════════════

# the LeaseListCreateView serves two main purposes: it allows property owners to view all leases associated with their properties and create new leases for tenants, while tenants can only view their own active leases. 
# The view uses different serializers to tailor the response based on the user's role, ensuring that owners and tenants see relevant information without exposing unnecessary details.
class LeaseListCreateView(APIView):
    """
    Owner — GET lists all leases on their properties
            POST creates a new lease for a tenant
    Tenant — GET returns their current active lease only
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if is_owner(request.user):
            # Owner sees all leases across all their properties
            leases     = Lease.objects.filter(
                unit__property__owner=request.user
            )
            serializer = LeaseOwnerSerializer(leases, many=True)

        elif is_tenant(request.user):
            # Tenant sees only their own leases
            leases     = Lease.objects.filter(tenant=request.user)
            serializer = LeaseTenantSerializer(leases, many=True)

        else:
            return Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(serializer.data)

    def post(self, request):
        if not is_owner(request.user):
            return Response(
                {'error': 'Only owners can create leases.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = LeaseCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        if serializer.is_valid():
            lease = serializer.save()
            return Response(
                LeaseOwnerSerializer(lease).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class LeaseDetailView(APIView):
    """
    GET   — Both Owner and Tenant view a lease
            (each sees their own serializer version)
    PATCH — Owner updates lease status
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            if is_owner(user):
                return Lease.objects.get(
                    pk=pk,
                    unit__property__owner=user,
                )
            else:
                return Lease.objects.get(pk=pk, tenant=user)
        except Lease.DoesNotExist:
            return None

    def get(self, request, pk):
        lease = self.get_object(pk, request.user)
        if not lease:
            return Response(
                {'error': 'Lease not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if is_owner(request.user):
            serializer = LeaseOwnerSerializer(lease)
        else:
            serializer = LeaseTenantSerializer(lease)

        return Response(serializer.data)


    def patch(self, request, pk):
        if not is_owner(request.user):
            return Response(
                {'error': 'Only owners can update lease status.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        lease = self.get_object(pk, request.user)
        if not lease:
            return Response(
                {'error': 'Lease not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = LeaseOwnerSerializer(
            lease,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()

            # If owner just agreed, check if tenant has also agreed
            # and activate the lease automatically
            lease.refresh_from_db()
            if lease.agreed_by_owner and lease.agreed_by_tenant:
                lease.status    = 'active'
                lease.agreed_at = timezone.now()
                lease.unit.is_occupied  = True
                lease.unit.is_available = False
                lease.unit.save()
                lease.save()

            return Response(LeaseOwnerSerializer(lease).data)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )



class LeaseAcceptView(APIView):
    """
    Tenant accepts a lease that has been
    created for them by an Owner.
    Marks agreed_by_tenant = True.
    If Owner has also agreed, activates the lease
    and marks unit as occupied.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_tenant(request.user):
            return Response(
                {'error': 'Only tenants can accept leases.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            lease = Lease.objects.get(pk=pk, tenant=request.user)
        except Lease.DoesNotExist:
            return Response(
                {'error': 'Lease not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        lease.agreed_by_tenant = True

        # If both parties have agreed, activate the lease
        if lease.agreed_by_owner and lease.agreed_by_tenant:
            lease.status    = 'active'
            lease.agreed_at = timezone.now()
            # Mark unit as occupied
            lease.unit.is_occupied  = True
            lease.unit.is_available = False
            lease.unit.save()

        lease.save()

        return Response({
            'message':         'Lease accepted.',
            'status':          lease.status,
            'agreed_by_tenant': lease.agreed_by_tenant,
        })



# ══════════════════════════════════════════════════════════════════════════
# RENT PAYMENT VIEWS
# ══════════════════════════════════════════════════════════════════════════

# The RentPaymentListCreateView serves a dual purpose: it allows property owners to view the payment history for all leases associated with their properties, while tenants can only view their own payment history and make new rent payments.
class RentPaymentListCreateView(APIView):
    """
    GET  — Both Owner and Tenant view payment history
    POST — Tenant makes a rent payment
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if is_owner(request.user):
            payments = RentPayment.objects.filter(
                lease__unit__property__owner=request.user
            )
        elif is_tenant(request.user):
            payments = RentPayment.objects.filter(
                lease__tenant=request.user
            )
        else:
            return Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RentPaymentSerializer(payments, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not is_tenant(request.user):
            return Response(
                {'error': 'Only tenants can make payments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RentPaymentCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        if serializer.is_valid():
            payment = serializer.save()
            return Response(
                RentPaymentSerializer(payment).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )



# ══════════════════════════════════════════════════════════════════════════
# MAINTENANCE REQUEST VIEWS
# ══════════════════════════════════════════════════════════════════════════

class MaintenanceRequestListCreateView(APIView):
    """
    GET  — Owner sees all requests on their properties
           Tenant sees only their own requests
    POST — Tenant raises a new request
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if is_owner(request.user):
            requests = MaintenanceRequest.objects.filter(
                unit__property__owner=request.user
            )
        elif is_tenant(request.user):
            requests = MaintenanceRequest.objects.filter(
                raised_by=request.user
            )
        else:
            return Response(
                {'error': 'Access denied.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MaintenanceRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not is_tenant(request.user):
            return Response(
                {'error': 'Only tenants can raise maintenance requests.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = MaintenanceRequestCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        if serializer.is_valid():
            req = serializer.save(raised_by=request.user)
            return Response(
                MaintenanceRequestSerializer(req).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class MaintenanceRequestDetailView(APIView):
    """
    GET   — Both Owner and Tenant view a request
    PATCH — Owner updates the status
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            if is_owner(user):
                return MaintenanceRequest.objects.get(
                    pk=pk,
                    unit__property__owner=user,
                )
            else:
                return MaintenanceRequest.objects.get(
                    pk=pk,
                    raised_by=user,
                )
        except MaintenanceRequest.DoesNotExist:
            return None

    def get(self, request, pk):
        req = self.get_object(pk, request.user)
        if not req:
            return Response(
                {'error': 'Request not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MaintenanceRequestSerializer(req)
        return Response(serializer.data)

    def patch(self, request, pk):
        if not is_owner(request.user):
            return Response(
                {'error': 'Only owners can update maintenance status.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        req = self.get_object(pk, request.user)
        if not req:
            return Response(
                {'error': 'Request not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MaintenanceStatusUpdateSerializer(
            req,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                MaintenanceRequestSerializer(req).data
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

