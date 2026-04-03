"""
URL configuration for kredhaus project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls    import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('accounts.urls')),     # accounts app will include endpoints for user registration, authentication, and profile management
    path('api/v1/tenancy/',  include('tenancy.urls')),      # tenancy app will include endpoints for managing properties, leases, and rent payments
    path('api/v1/messaging/', include('messaging.urls')),   # messaging app will include endpoints for managing conversations and messages between tenants, landlords, and other parties (e.g. neighbors, vendors)
    path('api/v1/utilities/', include('utilities.urls')),   # utilities app will include endpoints for managing utility accounts, bills, and supplier service requests
    path('api/v1/wallet/',      include('wallet.urls')),    # wallet app will include endpoints for managing tenant wallets, savings pockets, and transactions
    path('api/v1/financing/',   include('financing.urls')), # financing app will include endpoints for rent advances, utility advances, and credit builder loans
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)