from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UtilityViewSet, UtilityAccountViewSet, UtilityBillViewSet

router = DefaultRouter()
router.register(r'utilities', UtilityViewSet, basename='utility')
router.register(r'accounts', UtilityAccountViewSet, basename='utility-account')
router.register(r'bills', UtilityBillViewSet, basename='utility-bill')

urlpatterns = [
    path('', include(router.urls)),
]
