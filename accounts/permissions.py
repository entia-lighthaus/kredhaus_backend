from rest_framework.permissions import BasePermission


class IsKYCTier1(BasePermission):
    """
    This function allows access only to users who have
    completed KYC Tier 1 — phone + NIN verified.
    It is required for: basic payments, maintenance requests.
    """
    message = (
        'You need to complete KYC Tier 1 to access this feature. '
        'Please verify your phone number and NIN.'
    )

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.kyc_tier >= 1
        )


class IsKYCTier2(BasePermission):
    """
    This function allows access only to users who have
    completed KYC Tier 2 — BVN + address verified.
    Required for: rent payments, savings, credit building.
    """
    message = (
        'You need to complete KYC Tier 2 to access this feature. '
        'Please link your BVN and verify your address.'
    )

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.kyc_tier >= 2
        )


class IsKYCTier3(BasePermission):
    """
    Allows access only to users who have
    completed KYC Tier 3 — income + NOK verified.
    Required for: rent-to-own, BNPL, premium financing.
    """
    message = (
        'You need to complete KYC Tier 3 to access this feature. '
        'Please provide your income details and next of kin.'
    )

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.kyc_tier >= 3
        )