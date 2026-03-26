from django.test import TestCase
from accounts.models import User
from tenancy.models import Property, Unit, Lease
from .models import Utility, UtilityAccount, UtilityBill


class UtilityModelTest(TestCase):
    def setUp(self):
        self.utility = Utility.objects.create(
            name='electricity',
            display_name='EEDC Power',
            icon_color='#FDB913'
        )

    def test_utility_creation(self):
        self.assertEqual(self.utility.name, 'electricity')
        self.assertTrue(self.utility.is_active)


class UtilityAccountTest(TestCase):
    def setUp(self):
        # Create owner and property
        self.owner = User.objects.create_user(
            phone='2348012345678',
            password='testpass123',
            role='owner'
        )
        self.property = Property.objects.create(
            owner=self.owner,
            name='Test Property',
            property_type='flat',
            address='123 Main St',
            city='Lagos',
            lga='Ikeja',
            state='Lagos'
        )
        self.unit = Unit.objects.create(
            property=self.property,
            unit_number='Apt 101'
        )

        # Create utility
        self.utility = Utility.objects.create(
            name='electricity',
            display_name='EEDC Power'
        )

        # Create utility account
        self.account = UtilityAccount.objects.create(
            unit=self.unit,
            utility=self.utility,
            account_number='ELEC-001',
            provider='EEDC'
        )

    def test_utility_account_creation(self):
        self.assertEqual(self.account.account_number, 'ELEC-001')
        self.assertEqual(self.account.status, 'active')

    def test_unique_constraint(self):
        """Test that each utility can only be added once per unit."""
        with self.assertRaises(Exception):
            UtilityAccount.objects.create(
                unit=self.unit,
                utility=self.utility,
                account_number='ELEC-002'
            )
