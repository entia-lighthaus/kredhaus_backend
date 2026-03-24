from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    ProfileView,
    ProfileBuilderView,
    ProfileCompletionView,
    ProfilePhotoView,
    BVNVerificationView,
    NINVerificationView, 
    KYCStatusView,
    KYCTier1View,
    KYCTier2View,
    KYCTier3View,
    SetPINView,
    PINLoginView,
    DeviceListView,
    DeviceRevokeView,
    ReferralDashboardView,
    ReferralCreditHistoryView,
    DevVerifyPhoneView
)
    
urlpatterns = [

    # ── Auth ───────────────────────────────────────────────────────────
    path('register/',      RegisterView.as_view(),     name='register'),
    path('login/',         LoginView.as_view(),          name='login'),
    path('login/pin/',     PINLoginView.as_view(),       name='login-pin'),
    path('logout/',        LogoutView.as_view(),          name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(),   name='token-refresh'),

    # ── Profile ────────────────────────────────────────────────────────
    path('profile/',            ProfileView.as_view(),           name='profile'),
    path('profile/builder/',    ProfileBuilderView.as_view(),    name='profile-builder'),
    path('profile/completion/', ProfileCompletionView.as_view(), name='profile-completion'),
    path('profile/photo/',      ProfilePhotoView.as_view(),      name='profile-photo'),

    # ── Identity ───────────────────────────────────────────────────────
    path('verify/bvn/',    BVNVerificationView.as_view(), name='verify-bvn'),
    path('verify/nin/',    NINVerificationView.as_view(), name='verify-nin'),
    path('dev/verify-phone/', DevVerifyPhoneView.as_view(), name='dev-verify-phone'),

    # ── KYC ────────────────────────────────────────────────────────────
    path('kyc/status/',    KYCStatusView.as_view(),  name='kyc-status'),
    path('kyc/tier1/',     KYCTier1View.as_view(),   name='kyc-tier1'),
    path('kyc/tier2/',     KYCTier2View.as_view(),   name='kyc-tier2'),
    path('kyc/tier3/',     KYCTier3View.as_view(),   name='kyc-tier3'),

    # ── PIN & Devices ──────────────────────────────────────────────────
    path('pin/set/',                SetPINView.as_view(),    name='pin-set'),
    path('devices/',                DeviceListView.as_view(), name='device-list'),
    path('devices/<int:pk>/revoke/', DeviceRevokeView.as_view(), name='device-revoke'),

    # ── Referral ───────────────────────────────────────────────────────
    path('referral/',         ReferralDashboardView.as_view(),     name='referral-dashboard'),
    path('referral/credits/', ReferralCreditHistoryView.as_view(), name='referral-credits'),
]