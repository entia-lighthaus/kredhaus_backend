#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kredhaus.settings')
django.setup()

from utilities.models import Utility, Supplier, SupplierService, SupplierAvailability
from decimal import Decimal

# Get the Gas utility
gas_utility = Utility.objects.get(name='gas')

# Create sample suppliers
suppliers_data = [
    {
        'company_name': 'Oando Gas Co.',
        'phone_number': '+234701234567',
        'email': 'support@oandogas.com',
        'address': 'Lekki, Lagos',
        'city': 'Lagos',
        'average_rating': Decimal('4.8'),
        'total_reviews': 342,
        'delivery_fee': Decimal('1000'),
        'is_safety_certified': True,
        'icon_color': '#FF4500'
    },
    {
        'company_name': 'Total Gas Solutions',
        'phone_number': '+234702345678',
        'email': 'info@totalgassolutions.com',
        'address': 'Victoria Island, Lagos',
        'city': 'Lagos',
        'average_rating': Decimal('4.6'),
        'total_reviews': 287,
        'delivery_fee': Decimal('1200'),
        'is_safety_certified': True,
        'icon_color': '#FF6347'
    },
    {
        'company_name': 'Lagos Gas Supply',
        'phone_number': '+234703456789',
        'email': 'contact@lagosgassupply.com',
        'address': 'Ikeja, Lagos',
        'city': 'Lagos',
        'average_rating': Decimal('4.5'),
        'total_reviews': 156,
        'delivery_fee': Decimal('800'),
        'is_safety_certified': True,
        'icon_color': '#FF7F50'
    }
]

for supplier_data in suppliers_data:
    supplier, created = Supplier.objects.get_or_create(
        utility=gas_utility,
        phone_number=supplier_data['phone_number'],
        defaults={k: v for k, v in supplier_data.items() if k != 'phone_number'}
    )
    
    if created:
        # Create availability record
        SupplierAvailability.objects.create(
            supplier=supplier,
            is_online=True,
            current_orders=0,
            max_daily_orders=50
        )
        
        # Create sample services
        services = [
            {'name': '12kg Gas Cylinder Refill', 'price': Decimal('9500'), 'quantity': '12kg'},
            {'name': '6kg Gas Cylinder Refill', 'price': Decimal('5500'), 'quantity': '6kg'},
            {'name': 'Gas Top-up Delivery', 'price': Decimal('1500'), 'quantity': 'Varies'},
        ]
        
        for service in services:
            SupplierService.objects.create(
                supplier=supplier,
                **service,
                is_available=True
            )
        
        print(f" Created supplier: {supplier.company_name}")
    else:
        print(f"  Supplier already exists: {supplier.company_name}")

print("\n✅ Gas supplier seeding complete!")
