from django.urls import path
from .views import (
    RentAdvanceEligibilityView,
    RentAdvanceListCreateView,
    RentAdvanceDetailView,
    RentAdvanceRepayView,
    UtilityAdvanceListCreateView,
    CreditBuilderEligibilityView,
    CreditBuilderListCreateView,
    CreditBuilderDetailView,
    CreditBuilderRepayView,
)

app_name = 'financing'

urlpatterns = [

    # ── Rent Advance ───────────────────────────────────────────────────
    path(
        'rent-advance/eligibility/',
        RentAdvanceEligibilityView.as_view(),
        name='rent-advance-eligibility',
    ),
    path(
        'rent-advance/',
        RentAdvanceListCreateView.as_view(),
        name='rent-advance-list-create',
    ),
    path(
        'rent-advance/<uuid:pk>/',
        RentAdvanceDetailView.as_view(),
        name='rent-advance-detail',
    ),
    path(
        'rent-advance/<uuid:pk>/repay/',
        RentAdvanceRepayView.as_view(),
        name='rent-advance-repay',
    ),

    # ── Utility Advance ────────────────────────────────────────────────
    path(
        'utility-advance/',
        UtilityAdvanceListCreateView.as_view(),
        name='utility-advance-list-create',
    ),

    # ── Credit Builder ─────────────────────────────────────────────────
    path(
        'credit-builder/eligibility/',
        CreditBuilderEligibilityView.as_view(),
        name='credit-builder-eligibility',
    ),
    path(
        'credit-builder/',
        CreditBuilderListCreateView.as_view(),
        name='credit-builder-list-create',
    ),
    path(
        'credit-builder/<uuid:pk>/',
        CreditBuilderDetailView.as_view(),
        name='credit-builder-detail',
    ),
    path(
        'credit-builder/<uuid:pk>/repay/',
        CreditBuilderRepayView.as_view(),
        name='credit-builder-repay',
    ),
]