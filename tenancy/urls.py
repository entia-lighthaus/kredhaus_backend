from django.urls import path
from .views import (
    PropertyListCreateView,
    PropertyDetailView,
    UnitListCreateView,
    LeaseListCreateView,
    LeaseDetailView,
    LeaseAcceptView,
    RentPaymentListCreateView,
    MaintenanceRequestListCreateView,
    MaintenanceRequestDetailView,
)

app_name = 'tenancy'

urlpatterns = [

    # ── Properties ─────────────────────────────────────────────────────
    path(
        'properties/',
        PropertyListCreateView.as_view(),
        name='property-list-create',
    ),
    path(
        'properties/<int:pk>/',
        PropertyDetailView.as_view(),
        name='property-detail',
    ),

    # ── Units ──────────────────────────────────────────────────────────
    path(
        'properties/<int:property_pk>/units/',
        UnitListCreateView.as_view(),
        name='unit-list-create',
    ),

    # ── Leases ─────────────────────────────────────────────────────────
    path(
        'leases/',
        LeaseListCreateView.as_view(),
        name='lease-list-create',
    ),
    path(
        'leases/<int:pk>/',
        LeaseDetailView.as_view(),
        name='lease-detail',
    ),
    path(
        'leases/<int:pk>/accept/',
        LeaseAcceptView.as_view(),
        name='lease-accept',
    ),

    # ── Rent Payments ──────────────────────────────────────────────────
    path(
        'payments/',
        RentPaymentListCreateView.as_view(),
        name='payment-list-create',
    ),

    # ── Maintenance ────────────────────────────────────────────────────
    path(
        'maintenance/',
        MaintenanceRequestListCreateView.as_view(),
        name='maintenance-list-create',
    ),
    # The MaintenanceRequestDetailView allows tenants to view the details of their own maintenance requests and allows property owners to view and manage all maintenance requests for their properties. 
    # The view includes functionality for updating the status of a request, adding resolution notes, and marking requests as resolved.
    path(
        'maintenance/<int:pk>/',
        MaintenanceRequestDetailView.as_view(),
        name='maintenance-detail',
    ),
]