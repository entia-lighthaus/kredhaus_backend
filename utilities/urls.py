from django.urls import path, include
from rest_framework.routers import DefaultRouter

#from messaging import views
from .views import (
    UtilityViewSet, UtilityAccountViewSet, UtilityBillViewSet, UtilityRateViewSet,
    SupplierViewSet, SupplierServiceRequestViewSet, SupplierRatingViewSet, WaterSupplierListView,
    webhook_meter_reading, meter_reading_list
)

router = DefaultRouter()
router.register(r'utilities', UtilityViewSet, basename='utility')
router.register(r'accounts', UtilityAccountViewSet, basename='utility-account')
router.register(r'bills', UtilityBillViewSet, basename='utility-bill')
router.register(r'rates', UtilityRateViewSet, basename='utility-rate')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'service-requests', SupplierServiceRequestViewSet, basename='service-request')
router.register(r'supplier-ratings', SupplierRatingViewSet, basename='supplier-rating')

urlpatterns = [
    path('', include(router.urls)),
    path('webhooks/meter-reading/', webhook_meter_reading, name='webhook-meter-reading'),
    path('accounts/<int:account_id>/meter-readings/', meter_reading_list, name='meter-reading-list'),
    #path('water/suppliers/', views.WaterSupplierListView.as_view(), name='water-suppliers'),
    path('water/suppliers/', WaterSupplierListView.as_view(), name='water-suppliers'), 
]

