#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kredhaus.settings')
django.setup()

from utilities.models import (
    Utility, Supplier, SupplierService,
    SupplierAvailability, WaterSupplierDetail
)
from decimal import Decimal

# ── Helper ──────────────────────────────────────────────────────────────────

def get_utility(name):
    try:
        return Utility.objects.get(name=name)
    except Utility.DoesNotExist:
        print(f" Utility '{name}' not found. Run seed_utilities.py first.")
        return None


# ── Seed Data ────────────────────────────────────────────────────────────────

SUPPLIERS = [

    # ── GAS ──────────────────────────────────────────────────────────────────
    {
        'utility': 'gas',
        'company_name': 'Oando Gas Co.',
        'phone_number': '+234701234567',
        'email': 'support@oandogas.com',
        'address': 'Lekki Phase 1',
        'city': 'Lagos',
        'average_rating': Decimal('4.8'),
        'total_reviews': 342,
        'delivery_fee': Decimal('1000'),
        'pickup_time_minutes': 45,
        'is_safety_certified': True,
        'icon_color': '#FF4500',
        'services': [
            {'name': '12kg Cylinder Refill', 'price': Decimal('9500'),  'quantity': '12kg'},
            {'name': '6kg Cylinder Refill',  'price': Decimal('5500'),  'quantity': '6kg'},
            {'name': 'Gas Top-up Delivery',  'price': Decimal('1500'),  'quantity': 'Varies'},
        ],
        'availability': {'is_online': True, 'current_orders': 2, 'max_daily_orders': 50},
    },
    {
        'utility': 'gas',
        'company_name': 'Total Gas Solutions',
        'phone_number': '+234702345678',
        'email': 'info@totalgassolutions.com',
        'address': 'Victoria Island',
        'city': 'Lagos',
        'average_rating': Decimal('4.6'),
        'total_reviews': 287,
        'delivery_fee': Decimal('1200'),
        'pickup_time_minutes': 60,
        'is_safety_certified': True,
        'icon_color': '#FF6347',
        'services': [
            {'name': '12kg Cylinder Refill', 'price': Decimal('9800'),  'quantity': '12kg'},
            {'name': '6kg Cylinder Refill',  'price': Decimal('5700'),  'quantity': '6kg'},
        ],
        'availability': {'is_online': True, 'current_orders': 0, 'max_daily_orders': 40},
    },
    {
        'utility': 'gas',
        'company_name': 'Lagos Gas Supply',
        'phone_number': '+234703456789',
        'email': 'contact@lagosgassupply.com',
        'address': 'Ikeja',
        'city': 'Lagos',
        'average_rating': Decimal('4.5'),
        'total_reviews': 156,
        'delivery_fee': Decimal('800'),
        'pickup_time_minutes': 30,
        'is_safety_certified': True,
        'icon_color': '#FF7F50',
        'services': [
            {'name': '12kg Cylinder Refill', 'price': Decimal('9200'),  'quantity': '12kg'},
            {'name': '6kg Cylinder Refill',  'price': Decimal('5300'),  'quantity': '6kg'},
            {'name': '3kg Cylinder Refill',  'price': Decimal('3000'),  'quantity': '3kg'},
        ],
        'availability': {'is_online': True, 'current_orders': 5, 'max_daily_orders': 60},
    },
    {
        'utility': 'gas',
        'company_name': 'Ardova Gas',
        'phone_number': '+234704567890',
        'email': 'gas@ardova.com',
        'address': 'Surulere',
        'city': 'Lagos',
        'average_rating': Decimal('4.7'),
        'total_reviews': 421,
        'delivery_fee': Decimal('900'),
        'pickup_time_minutes': 40,
        'is_safety_certified': True,
        'icon_color': '#FF8C00',
        'services': [
            {'name': '12.5kg Cylinder Refill', 'price': Decimal('9900'), 'quantity': '12.5kg'},
            {'name': '6kg Cylinder Refill',    'price': Decimal('5400'), 'quantity': '6kg'},
        ],
        'availability': {'is_online': True, 'current_orders': 1, 'max_daily_orders': 45},
    },

    # ── WATER (SACHET) ────────────────────────────────────────────────────────
    {
        'utility': 'water',
        'company_name': 'Crystal Pure Water',
        'phone_number': '+234711111111',
        'email': 'hello@crystalpure.ng',
        'address': '15 Agege Motor Road',
        'city': 'Ikeja, Lagos',
        'average_rating': Decimal('4.9'),
        'total_reviews': 567,
        'delivery_fee': Decimal('500'),
        'pickup_time_minutes': 45,
        'is_safety_certified': True,
        'icon_color': '#00BFFF',
        'services': [
            {'name': 'Sachet Water (1 Bag)',  'price': Decimal('150'), 'quantity': '1 bag (50 sachets)'},
            {'name': 'Sachet Water (5 Bags)', 'price': Decimal('700'), 'quantity': '5 bags'},
        ],
        'availability': {'is_online': True, 'current_orders': 3, 'max_daily_orders': 100},
        # Water-specific
        'water_detail': {
            'water_type': 'sachet',
            'sachets_per_bag': 50,
            'ml_per_sachet': 500,
            'min_order_bags': 2,
            'nafdac_certified': True,
        },
    },
    {
        'utility': 'water',
        'company_name': 'Aqua Fresh Supplies',
        'phone_number': '+234722222222',
        'email': 'orders@aquafresh.ng',
        'address': 'Admiralty Way',
        'city': 'Lekki, Lagos',
        'average_rating': Decimal('4.6'),
        'total_reviews': 312,
        'delivery_fee': Decimal('500'),
        'pickup_time_minutes': 60,
        'is_safety_certified': True,
        'icon_color': '#1E90FF',
        'services': [
            {'name': 'Sachet Water (1 Bag)',   'price': Decimal('140'), 'quantity': '1 bag (50 sachets)'},
            {'name': 'Sachet Water (10 Bags)', 'price': Decimal('1300'), 'quantity': '10 bags'},
        ],
        'availability': {'is_online': True, 'current_orders': 1, 'max_daily_orders': 80},
        'water_detail': {
            'water_type': 'sachet',
            'sachets_per_bag': 50,
            'ml_per_sachet': 500,
            'min_order_bags': 1,
            'nafdac_certified': True,
        },
    },
    {
        'utility': 'water',
        'company_name': 'Pure Life Water Co.',
        'phone_number': '+234733333333',
        'email': 'info@purelife.ng',
        'address': 'Adeola Odeku Street',
        'city': 'Victoria Island, Lagos',
        'average_rating': Decimal('4.4'),
        'total_reviews': 198,
        'delivery_fee': Decimal('600'),
        'pickup_time_minutes': 50,
        'is_safety_certified': True,
        'icon_color': '#4169E1',
        'services': [
            {'name': 'Sachet Water (1 Bag)', 'price': Decimal('160'), 'quantity': '1 bag (50 sachets)'},
        ],
        'availability': {'is_online': False, 'current_orders': 0, 'max_daily_orders': 60},
        'water_detail': {
            'water_type': 'sachet',
            'sachets_per_bag': 50,
            'ml_per_sachet': 500,
            'min_order_bags': 2,
            'nafdac_certified': True,
        },
    },

    # ── WATER (TANKER) ────────────────────────────────────────────────────────
    {
        'utility': 'water',
        'company_name': 'Lagos Water Tankers',
        'phone_number': '+234744444444',
        'email': 'dispatch@lagostankers.ng',
        'address': 'Lagos Island',
        'city': 'Lagos',
        'average_rating': Decimal('4.7'),
        'total_reviews': 189,
        'delivery_fee': Decimal('0'),
        'pickup_time_minutes': 120,
        'is_safety_certified': True,
        'icon_color': '#0000CD',
        'services': [
            {'name': '5,000L Water Tanker',  'price': Decimal('15000'), 'quantity': '5,000 litres'},
            {'name': '10,000L Water Tanker', 'price': Decimal('25000'), 'quantity': '10,000 litres'},
        ],
        'availability': {'is_online': True, 'current_orders': 2, 'max_daily_orders': 20},
        'water_detail': {
            'water_type': 'tanker',
            'nafdac_certified': False,
            'volume_options': [
                {'litres': 5000,  'price': 15000},
                {'litres': 10000, 'price': 25000},
            ],
            'free_delivery_threshold': Decimal('15000'),
        },
    },
    {
        'utility': 'water',
        'company_name': 'AquaBulk Solutions',
        'phone_number': '+234755555555',
        'email': 'bulk@aquabulk.ng',
        'address': 'Apapa',
        'city': 'Lagos',
        'average_rating': Decimal('4.5'),
        'total_reviews': 143,
        'delivery_fee': Decimal('0'),
        'pickup_time_minutes': 150,
        'is_safety_certified': True,
        'icon_color': '#191970',
        'services': [
            {'name': '5,000L Water Tanker',  'price': Decimal('14000'), 'quantity': '5,000 litres'},
            {'name': '10,000L Water Tanker', 'price': Decimal('23000'), 'quantity': '10,000 litres'},
        ],
        'availability': {'is_online': True, 'current_orders': 0, 'max_daily_orders': 15},
        'water_detail': {
            'water_type': 'tanker',
            'nafdac_certified': False,
            'volume_options': [
                {'litres': 5000,  'price': 14000},
                {'litres': 10000, 'price': 23000},
            ],
            'free_delivery_threshold': Decimal('14000'),
        },
    },

    # ── INTERNET ──────────────────────────────────────────────────────────────
    {
        'utility': 'internet',
        'company_name': 'Spectranet',
        'phone_number': '+234761111111',
        'email': 'support@spectranet.com.ng',
        'address': 'Broad Street',
        'city': 'Lagos',
        'average_rating': Decimal('4.2'),
        'total_reviews': 1204,
        'delivery_fee': Decimal('0'),
        'pickup_time_minutes': 0,
        'is_safety_certified': True,
        'icon_color': '#8A2BE2',
        'services': [
            {'name': '10 Mbps Monthly Plan',  'price': Decimal('15000'), 'quantity': '10 Mbps'},
            {'name': '20 Mbps Monthly Plan',  'price': Decimal('25000'), 'quantity': '20 Mbps'},
            {'name': '50 Mbps Monthly Plan',  'price': Decimal('45000'), 'quantity': '50 Mbps'},
            {'name': '100 Mbps Monthly Plan', 'price': Decimal('75000'), 'quantity': '100 Mbps'},
        ],
        'availability': {'is_online': True, 'current_orders': 0, 'max_daily_orders': 999},
    },
    {
        'utility': 'internet',
        'company_name': 'Smile Communications',
        'phone_number': '+234762222222',
        'email': 'hello@smile.com.ng',
        'address': 'Adeola Hopewell Street',
        'city': 'Victoria Island, Lagos',
        'average_rating': Decimal('4.0'),
        'total_reviews': 876,
        'delivery_fee': Decimal('0'),
        'pickup_time_minutes': 0,
        'is_safety_certified': True,
        'icon_color': '#FF1493',
        'services': [
            {'name': '25GB Data Bundle',  'price': Decimal('5000'),  'quantity': '25GB'},
            {'name': '50GB Data Bundle',  'price': Decimal('8500'),  'quantity': '50GB'},
            {'name': '100GB Data Bundle', 'price': Decimal('15000'), 'quantity': '100GB'},
            {'name': 'Unlimited Monthly', 'price': Decimal('20000'), 'quantity': 'Unlimited'},
        ],
        'availability': {'is_online': True, 'current_orders': 0, 'max_daily_orders': 999},
    },
    {
        'utility': 'internet',
        'company_name': 'ipNX Nigeria',
        'phone_number': '+234763333333',
        'email': 'residential@ipnx.com.ng',
        'address': 'Opebi Road',
        'city': 'Ikeja, Lagos',
        'average_rating': Decimal('4.5'),
        'total_reviews': 634,
        'delivery_fee': Decimal('0'),
        'pickup_time_minutes': 0,
        'is_safety_certified': True,
        'icon_color': '#006400',
        'services': [
            {'name': 'Home 10 Mbps',  'price': Decimal('18000'), 'quantity': '10 Mbps fibre'},
            {'name': 'Home 20 Mbps',  'price': Decimal('28000'), 'quantity': '20 Mbps fibre'},
            {'name': 'Home 50 Mbps',  'price': Decimal('48000'), 'quantity': '50 Mbps fibre'},
        ],
        'availability': {'is_online': True, 'current_orders': 0, 'max_daily_orders': 999},
    },
    {
        'utility': 'internet',
        'company_name': 'MTN Broadband',
        'phone_number': '+234764444444',
        'email': 'broadband@mtn.ng',
        'address': 'Marina',
        'city': 'Lagos',
        'average_rating': Decimal('3.8'),
        'total_reviews': 2341,
        'delivery_fee': Decimal('0'),
        'pickup_time_minutes': 0,
        'is_safety_certified': True,
        'icon_color': '#FFD700',
        'services': [
            {'name': '30GB Monthly',       'price': Decimal('6000'),  'quantity': '30GB'},
            {'name': '60GB Monthly',       'price': Decimal('10000'), 'quantity': '60GB'},
            {'name': 'Unlimited Monthly',  'price': Decimal('22000'), 'quantity': 'Unlimited'},
        ],
        'availability': {'is_online': True, 'current_orders': 0, 'max_daily_orders': 999},
    },
]


# ── Runner ───────────────────────────────────────────────────────────────────

def run():
    print("\n🌱 Starting supplier seed...\n")

    for data in SUPPLIERS:
        utility = get_utility(data['utility'])
        if not utility:
            continue

        supplier, created = Supplier.objects.get_or_create(
            utility=utility,
            phone_number=data['phone_number'],
            defaults={
                'company_name':         data['company_name'],
                'email':                data.get('email', ''),
                'address':              data.get('address', ''),
                'city':                 data.get('city', ''),
                'average_rating':       data['average_rating'],
                'total_reviews':        data['total_reviews'],
                'delivery_fee':         data['delivery_fee'],
                'pickup_time_minutes':  data.get('pickup_time_minutes', 30),
                'is_safety_certified':  data['is_safety_certified'],
                'icon_color':           data.get('icon_color', '#000000'),
                'status':               'active',
                'is_available':         True,
            }
        )

        if created:
            # Availability
            avail = data.get('availability', {})
            SupplierAvailability.objects.create(
                supplier=supplier,
                is_online=avail.get('is_online', True),
                current_orders=avail.get('current_orders', 0),
                max_daily_orders=avail.get('max_daily_orders', 50),
            )

            # Services
            for svc in data.get('services', []):
                SupplierService.objects.create(
                    supplier=supplier,
                    name=svc['name'],
                    price=svc['price'],
                    quantity=svc.get('quantity', ''),
                    is_available=True,
                )

            # Water detail (only for water suppliers)
            if 'water_detail' in data:
                wd = data['water_detail']
                WaterSupplierDetail.objects.create(
                    supplier=supplier,
                    water_type=wd['water_type'],
                    sachets_per_bag=wd.get('sachets_per_bag', 50),
                    ml_per_sachet=wd.get('ml_per_sachet', 500),
                    min_order_bags=wd.get('min_order_bags', 1),
                    nafdac_certified=wd.get('nafdac_certified', False),
                    volume_options=wd.get('volume_options', []),
                    free_delivery_threshold=wd.get('free_delivery_threshold', None),
                )

            print(f"   {utility.display_name} | {supplier.company_name}")
        else:
            print(f"  ⏭️  Already exists: {supplier.company_name}")

    print("\n Supplier seeding complete!")
    print(f"   Gas:      {Supplier.objects.filter(utility__name='gas').count()} suppliers")
    print(f"   Water:    {Supplier.objects.filter(utility__name='water').count()} suppliers")
    print(f"   Internet: {Supplier.objects.filter(utility__name='internet').count()} suppliers")


if __name__ == '__main__':
    run()