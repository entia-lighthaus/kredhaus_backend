# This file defines the API views for our financing products: Rent Advance, Utility Advance, and Credit Builder Loan.
# Each product has its own set of views for checking eligibility, listing existing advances/loans and creating new ones. 
# The views interact with the services layer to perform the necessary business logic and return appropriate responses.
from django.shortcuts import render
from rest_framework              import status
from rest_framework.views        import APIView
from rest_framework.response     import Response
from rest_framework.permissions  import IsAuthenticated

from wallet.services  import WalletService
from tenancy.models   import Lease
from .models          import RentAdvance, UtilityAdvance, CreditBuilderLoan
from .services        import (
    EligibilityService,
    RentAdvanceService,
    CreditBuilderService,
)
from .serializers import (
    RentAdvanceSerializer,
    RentAdvanceCreateSerializer,
    UtilityAdvanceSerializer,
    UtilityAdvanceCreateSerializer,
    CreditBuilderLoanSerializer,
    CreditBuilderCreateSerializer,
)


# ══════════════════════════════════════════════════════════════════════════
# RENT ADVANCE
# ══════════════════════════════════════════════════════════════════════════

class RentAdvanceEligibilityView(APIView):
    """
    GET — check if the current user is eligible
    for a rent advance and how much they can get.
    Called when user opens the Rent Advance screen.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get active lease
        lease = Lease.objects.filter(
            tenant=request.user,
            status='active',
        ).first()

        if not lease:
            return Response({
                'eligible':    False,
                'reason':      'No active lease found on Kredhaus.',
                'max_amount':  0,
            })

        # Check with dummy amount to get reason
        from django.conf import settings
        from decimal import Decimal
        max_amount = lease.rent_amount * Decimal(
            settings.RENT_ADVANCE_MAX_PERCENT / 100
        )

        eligible, reason = EligibilityService.check_rent_advance(
            user              = request.user,
            lease             = lease,
            amount_requested  = max_amount,
        )

        return Response({
            'eligible':         eligible,
            'reason':           reason,
            'max_amount':       max_amount,
            'rent_amount':      lease.rent_amount,
            'lease_id':         lease.id,
            'rent_frequency':   lease.rent_frequency,
        })


class RentAdvanceListCreateView(APIView):
    """
    GET  — list all rent advances for current user
    POST — apply for a new rent advance
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        advances   = RentAdvance.objects.filter(tenant=request.user)
        serializer = RentAdvanceSerializer(advances, many=True)
        return Response({'advances': serializer.data})

    def post(self, request):
        serializer = RentAdvanceCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Get the lease
        try:
            lease = Lease.objects.get(
                id=data['lease_id'],
                tenant=request.user,
                status='active',
            )
        except Lease.DoesNotExist:
            return Response(
                {'error': 'Active lease not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Eligibility check
        eligible, reason = EligibilityService.check_rent_advance(
            user             = request.user,
            lease            = lease,
            amount_requested = data['amount_requested'],
        )
        if not eligible:
            return Response(
                {'error': reason},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get wallet
        wallet, _ = WalletService.get_or_create_wallet(request.user)

        # Create advance
        advance = RentAdvanceService.create_advance(
            user              = request.user,
            lease             = lease,
            amount_requested  = data['amount_requested'],
            repayment_months  = data['repayment_months'],
            wallet            = wallet,
        )

        return Response(
            RentAdvanceSerializer(advance).data,
            status=status.HTTP_201_CREATED,
        )


class RentAdvanceDetailView(APIView):
    """
    GET — view a specific rent advance
    with full repayment schedule.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            advance = RentAdvance.objects.get(
                id=pk,
                tenant=request.user,
            )
        except RentAdvance.DoesNotExist:
            return Response(
                {'error': 'Advance not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RentAdvanceSerializer(advance)
        return Response(serializer.data)


# The RentAdvanceRepayView allows tenants to make repayments towards their rent advance. In production, repayments will be processed automatically on their due dates via a scheduled task (e.g., using AWS Lambda). 
# However, this endpoint provides the flexibility for tenants to make manual payments if they wish to pay early or if they want to trigger a payment outside of the scheduled process.
class RentAdvanceRepayView(APIView):
    """
    POST — manually trigger a repayment
    for the next instalment.
    In production this runs automatically
    via a scheduled task on the due date. 
    This endpoint is for manual payments if tenant wants to pay early or trigger outside of schedule.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            advance = RentAdvance.objects.get(
                id=pk,
                tenant=request.user,
                status='active',
            )
        except RentAdvance.DoesNotExist:
            return Response(
                {'error': 'Active advance not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        wallet, _ = WalletService.get_or_create_wallet(request.user)
        repayment, message = RentAdvanceService.process_repayment(
            advance, wallet
        )

        if not repayment:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'message':          'Repayment processed successfully.',
            'instalment':       repayment.instalment_number,
            'amount':           repayment.amount,
            'advance_status':   advance.status,
            'amount_remaining': advance.amount_remaining,
        })


# ══════════════════════════════════════════════════════════════════════════
# UTILITY ADVANCE
# ══════════════════════════════════════════════════════════════════════════

class UtilityAdvanceListCreateView(APIView):
    """
    GET  — list all utility advances
    POST — apply for a utility advance
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        advances   = UtilityAdvance.objects.filter(tenant=request.user)
        serializer = UtilityAdvanceSerializer(advances, many=True)
        return Response({'advances': serializer.data})

    def post(self, request):
        serializer = UtilityAdvanceCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Eligibility check
        eligible, reason = EligibilityService.check_utility_advance(
            user             = request.user,
            amount_requested = float(data['amount_requested']),
        )
        if not eligible:
            return Response(
                {'error': reason},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculate financials
        from django.conf import settings
        fees         = settings.UTILITY_ADVANCE_FEES
        months       = data['repayment_months']
        fee_percent  = fees.get(months, 3.5)
        amount       = data['amount_requested']
        fee_amount   = amount * fee_percent / 100
        total        = amount + fee_amount
        monthly      = total / int(months)

        wallet, _ = WalletService.get_or_create_wallet(request.user)

        advance = UtilityAdvance.objects.create(
            tenant            = request.user,
            wallet            = wallet,
            utility_type      = data['utility_type'],
            provider_name     = data['provider_name'],
            account_number    = data.get('account_number', ''),
            amount_requested  = amount,
            flat_fee_percent  = fee_percent,
            flat_fee_amount   = fee_amount,
            total_repayable   = total,
            repayment_months  = months,
            monthly_repayment = monthly,
            status            = 'active',
            disbursed_at      = __import__('django.utils.timezone', fromlist=['timezone']).timezone.now(),
        )

        # Generate repayment schedule
        from datetime import date
        from dateutil.relativedelta import relativedelta
        today = date.today()
        from .models import UtilityAdvanceRepayment
        for i in range(1, int(months) + 1):
            UtilityAdvanceRepayment.objects.create(
                advance           = advance,
                amount            = monthly,
                due_date          = today + relativedelta(months=i),
                instalment_number = i,
                status            = 'upcoming',
            )

        return Response(
            UtilityAdvanceSerializer(advance).data,
            status=status.HTTP_201_CREATED,
        )


# ══════════════════════════════════════════════════════════════════════════
# CREDIT BUILDER LOAN
# ══════════════════════════════════════════════════════════════════════════

class CreditBuilderEligibilityView(APIView):
    """
    GET — check eligibility for credit builder loan.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        eligible, reason = EligibilityService.check_credit_builder(
            request.user
        )
        return Response({
            'eligible':       eligible,
            'reason':         reason,
            'available_amounts': [50000, 100000, 150000, 200000],
            'available_plans':  ['6', '12'],
            'monthly_fee':      1500,
        })


class CreditBuilderListCreateView(APIView):
    """
    GET  — list all credit builder loans
    POST — apply for a credit builder loan
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loans      = CreditBuilderLoan.objects.filter(tenant=request.user)
        serializer = CreditBuilderLoanSerializer(loans, many=True)
        return Response({'loans': serializer.data})

    def post(self, request):
        serializer = CreditBuilderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Eligibility check
        eligible, reason = EligibilityService.check_credit_builder(
            request.user
        )
        if not eligible:
            return Response(
                {'error': reason},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet, _ = WalletService.get_or_create_wallet(request.user)

        # Check wallet has enough to fund vault
        from decimal import Decimal
        loan_amount = Decimal(str(data['loan_amount']))
        if not wallet.can_debit(loan_amount):
            return Response(
                {
                    'error': (
                        f'Insufficient wallet balance. '
                        f'You need ₦{loan_amount:,} in your wallet '
                        f'to start a Credit Builder Loan. '
                        f'Please fund your wallet first.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            loan = CreditBuilderService.create_loan(
                user        = request.user,
                loan_amount = loan_amount,
                plan_months = data['plan_months'],
                wallet      = wallet,
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            CreditBuilderLoanSerializer(loan).data,
            status=status.HTTP_201_CREATED,
        )


class CreditBuilderDetailView(APIView):
    """
    GET — view a credit builder loan
    with full repayment schedule.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            loan = CreditBuilderLoan.objects.get(
                id=pk,
                tenant=request.user,
            )
        except CreditBuilderLoan.DoesNotExist:
            return Response(
                {'error': 'Loan not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CreditBuilderLoanSerializer(loan)
        return Response(serializer.data)


class CreditBuilderRepayView(APIView):
    """
    POST — process next credit builder repayment.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            loan = CreditBuilderLoan.objects.get(
                id=pk,
                tenant=request.user,
                status='active',
            )
        except CreditBuilderLoan.DoesNotExist:
            return Response(
                {'error': 'Active loan not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        wallet, _ = WalletService.get_or_create_wallet(request.user)
        repayment, message = CreditBuilderService.process_repayment(
            loan, wallet
        )

        if not repayment:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'message':          'Repayment processed.',
            'instalment':       repayment.instalment_number,
            'amount':           repayment.monthly_total,
            'loan_status':      loan.status,
            'payments_made':    loan.payments_made,
            'payments_remaining': loan.payments_remaining,
        })