from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, ProfileView, LogoutView, NINVerificationView, BVNVerificationView, KYCStatusView, KYCTier1View, KYCTier2View, KYCTier3View

urlpatterns = [
    path('register/',      RegisterView.as_view(),     name='register'),
    path('login/',         LoginView.as_view(),         name='login'),
    path('profile/',       ProfileView.as_view(),       name='profile'),
    path('token/refresh/', TokenRefreshView.as_view(),  name='token-refresh'),
    path('logout/',        LogoutView.as_view(),         name='logout'),
    
    #BVN AND NIN VIEWS 
    path('verify/nin/',    NINVerificationView.as_view(), name='verify-nin'),
    path('verify/bvn/',    BVNVerificationView.as_view(), name='verify-bvn'),
    
    #KYC VIEWS
    path('kyc/status/',    KYCStatusView.as_view(),       name='kyc-status'),
    path('kyc/tier1/',     KYCTier1View.as_view(),        name='kyc-tier1'),
    path('kyc/tier2/',     KYCTier2View.as_view(),        name='kyc-tier2'),
    path('kyc/tier3/',     KYCTier3View.as_view(),        name='kyc-tier3'),

]