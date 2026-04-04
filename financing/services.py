# financing/services.py
# This module contains the core business logic for our financing products, including rent advances, utility advances, and credit builder loans. 
# It defines services that handle the creation of advances and loans, calculation of repayment schedules, and processing of repayments. 
# By centralizing this logic in services, we keep our views thin and focused on handling HTTP requests and responses, while the services manage the complex financial operations and interactions with the wallet system.
from decimal import Decimal
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.conf import settings

from wallet.models   import Wallet, SavingsPocket
from wallet.services import WalletService, generate_reference
from .models import (
    RentAdvance, RentAdvanceRepayment,
    UtilityAdvance, UtilityAdvanceRepayment,
    CreditBuilderLoan, CreditBuilderRepayment,
)


class EligibilityService:

    @staticmethod
    def check_rent_advance(user, lease, amount_requested):
        """
        Returns (is_eligible: bool, reason: str)
        """
        from tenancy.models import RentPayment

        # KYC check
        if user.kyc_tier < 2:
            return False, 'KYC Tier 2 required for Rent Advance.'

        # Active lease check
        if lease.status != 'active':
            return False, 'You must have an active lease.'

        # No existing active advance
        if RentAdvance.objects.filter(
            tenant=user, status='active'
        ).exists():
            return False, 'You already have an active Rent Advance.'

        # Minimum 3 months payment history
        payment_count = RentPayment.objects.filter(
            lease__tenant=user,
            status='completed',
        ).count()
        if payment_count < 1:
            months_needed = 3 - payment_count
            return (
                False,
                f'You need {months_needed} more payment(s) to qualify.',
            )

        # Amount check — max 50% of rent cycle
        max_amount = lease.rent_amount * Decimal(
            settings.RENT_ADVANCE_MAX_PERCENT / 100
        )
        if Decimal(str(amount_requested)) > max_amount:
            return (
                False,
                f'Maximum advance is ₦{max_amount:,} '
                f'({settings.RENT_ADVANCE_MAX_PERCENT}% of your rent).',
            )

        return True, 'Eligible'

    @staticmethod
    def check_utility_advance(user, amount_requested):
        """Check eligibility for utility advance."""
        if user.kyc_tier < 1:
            return False, 'KYC Tier 1 required for Utility Advance.'

        if amount_requested > settings.UTILITY_ADVANCE_MAX:
            return (
                False,
                f'Maximum utility advance is '
                f'₦{settings.UTILITY_ADVANCE_MAX:,}.',
            )

        active_count = UtilityAdvance.objects.filter(
            tenant=user,
            status='active',
        ).count()
        if active_count >= 2:
            return (
                False,
                'Maximum of 2 active utility advances allowed.',
            )

        return True, 'Eligible'

    @staticmethod
    def check_credit_builder(user):
        """Check eligibility for credit builder loan."""
        if user.kyc_tier < 2:
            return False, 'KYC Tier 2 required for Credit Builder Loan.'

        if CreditBuilderLoan.objects.filter(
            tenant=user, status='active'
        ).exists():
            return (
                False,
                'You already have an active Credit Builder Loan.',
            )

        return True, 'Eligible'


class RentAdvanceService:

    @staticmethod
    def create_advance(user, lease, amount_requested,
                       repayment_months, wallet):
        """
        Creates a rent advance, calculates financials,
        generates repayment schedule, and disburses
        funds to the landlord's wallet.
        """
        advance = RentAdvance(
            tenant            = user,
            lease             = lease,
            wallet            = wallet,
            amount_requested  = amount_requested,
            amount_approved   = amount_requested,
            repayment_months  = str(repayment_months),
        )
        advance.calculate_financials()
        advance.status       = 'active'
        advance.disbursed_at = timezone.now()
        advance.save()

        # Generate repayment schedule
        today = date.today()
        for i in range(1, int(repayment_months) + 1):
            due_date = today + relativedelta(months=i)
            CreditBuilderRepayment if False else \
            RentAdvanceRepayment.objects.create(
                advance            = advance,
                amount             = advance.monthly_repayment,
                due_date           = due_date,
                instalment_number  = i,
                status             = 'upcoming',
            )

        # Disburse to landlord wallet
        try:
            landlord       = lease.unit.property.owner
            landlord_wallet, _ = WalletService.get_or_create_wallet(
                landlord
            )
            WalletService.credit_wallet(
                wallet           = landlord_wallet,
                amount           = advance.amount_approved,
                transaction_type = 'advance_credit',
                description      = (
                    f'Rent advance from {user.first_name} '
                    f'{user.last_name} via Kredhaus'
                ),
                metadata         = {'advance_id': str(advance.id)},
            )
        except Exception:
            pass   # log in production — don't block creation

        return advance

    @staticmethod
    def process_repayment(advance, wallet):
        """
        Debit the tenant's wallet for the next
        due repayment instalment.
        """
        next_repayment = advance.repayments.filter(
            status='upcoming'
        ).order_by('instalment_number').first()

        if not next_repayment:
            return None, 'No upcoming repayments.'

        try:
            transaction = WalletService.debit_wallet(
                wallet           = wallet,
                amount           = next_repayment.amount,
                transaction_type = 'advance_repay',
                description      = (
                    f'Rent Advance repayment '
                    f'{next_repayment.instalment_number} of '
                    f'{advance.repayment_months}'
                ),
            )
        except ValueError as e:
            return None, str(e)

        next_repayment.status    = 'paid'
        next_repayment.paid_date = timezone.now()
        next_repayment.transaction = transaction
        next_repayment.save()

        # Check if fully repaid
        if not advance.repayments.filter(status='upcoming').exists():
            advance.status       = 'completed'
            advance.completed_at = timezone.now()
            advance.save()

        return next_repayment, 'Success'


class CreditBuilderService:

    @staticmethod # This method creates a credit builder loan, which is a unique product that combines a locked savings pocket (the vault) with a repayment schedule. 
    # The loan amount is moved into the vault, and as the borrower makes repayments, the principal portion is credited back to the vault. Once all repayments are made, the vault is released back to the borrower's main wallet. 
    # This structure helps users build credit history while also encouraging disciplined saving.
    def create_loan(user, loan_amount, plan_months, wallet):
        """
        Creates a credit builder loan:
        1. Creates a locked savings pocket (the vault)
        2. Deducts the loan amount from wallet into vault
        3. Generates repayment schedule
        """
        # Create locked vault pocket
        vault_pocket = SavingsPocket.objects.create(
            wallet        = wallet,
            name          = 'Credit Builder Vault',
            pocket_type   = 'credit_vault',
            target_amount = Decimal(str(loan_amount)),
            is_locked     = True,
        )

        # Move loan amount from wallet to vault
        try:
            WalletService.transfer_to_pocket(
                wallet      = wallet,
                pocket      = vault_pocket,
                amount      = Decimal(str(loan_amount)),
                description = 'Credit Builder Loan vault deposit',
            )
        except ValueError as e:
            vault_pocket.delete()
            raise ValueError(str(e))

        # Create loan record
        loan = CreditBuilderLoan(
            tenant      = user,
            wallet      = wallet,
            vault_pocket = vault_pocket,
            loan_amount = Decimal(str(loan_amount)),
            plan_months = str(plan_months),
        )
        loan.calculate_financials()
        loan.save()

        # Generate repayment schedule
        today = date.today()
        for i in range(1, int(plan_months) + 1):
            due_date = today + relativedelta(months=i)
            CreditBuilderRepayment.objects.create(
                loan               = loan,
                instalment_number  = i,
                principal_amount   = loan.monthly_principal,
                fee_amount         = loan.monthly_fee,
                monthly_total      = loan.monthly_total,
                due_date           = due_date,
                status             = 'upcoming',
            )

        return loan

    @staticmethod
    def process_repayment(loan, wallet):
        """
        Debit wallet for the next credit builder
        repayment. Credit the principal portion
        back into the vault.
        """
        next_repayment = loan.repayments.filter(
            status='upcoming'
        ).order_by('instalment_number').first()

        if not next_repayment:
            return None, 'No upcoming repayments.'

        try:
            transaction = WalletService.debit_wallet(
                wallet           = wallet,
                amount           = next_repayment.monthly_total,
                transaction_type = 'advance_repay',
                description      = (
                    f'Credit Builder repayment '
                    f'{next_repayment.instalment_number} of '
                    f'{loan.plan_months}'
                ),
            )
        except ValueError as e:
            return None, str(e)

        next_repayment.status      = 'paid'
        next_repayment.paid_date   = timezone.now()
        next_repayment.transaction = transaction
        next_repayment.save()

        # Rebuild vault balance with principal portion
        loan.vault_pocket.credit(next_repayment.principal_amount)

        # Check if loan is complete
        if not loan.repayments.filter(status='upcoming').exists():
            # Release vault to main wallet
            vault_balance = loan.vault_pocket.balance
            loan.vault_pocket.is_locked = False
            loan.vault_pocket.save()
            WalletService.withdraw_from_pocket(
                wallet      = wallet,
                pocket      = loan.vault_pocket,
                amount      = vault_balance,
                description = 'Credit Builder Loan completed — vault released',
            )
            loan.status       = 'completed'
            loan.completed_at = timezone.now()
            loan.save()

        return next_repayment, 'Success'