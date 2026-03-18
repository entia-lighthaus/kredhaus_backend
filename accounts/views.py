from rest_framework              import status
from rest_framework.views        import APIView
from rest_framework.response     import Response
from rest_framework.permissions  import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer, NINVerificationSerializer, BVNVerificationSerializer, KYCTier1Serializer, KYCTier2Serializer, KYCTier3Serializer, KYCStatusSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    'message': 'Account created successfully.',
                    'user': {
                        'phone':      user.phone,
                        'first_name': user.first_name,
                        'last_name':  user.last_name,
                        'role':       user.role,
                    }
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user    = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'Login successful.',
                'tokens': {
                    'access':  str(refresh.access_token),
                    'refresh': str(refresh),
                },
                'user': {
                    'phone':      user.phone,
                    'first_name': user.first_name,
                    'last_name':  user.last_name,
                    'role':       user.role,
                }
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


#logoutview
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully.'})

        except TokenError:
            return Response(
                {'error': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

# NIN AND BVN INFO
class NINVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = NINVerificationSerializer(data=request.data)

        if serializer.is_valid():
            nin  = serializer.validated_data['nin']
            user = request.user

            # In production this is where you call NIMC or Smile Identity API
            # For now we simulate a successful verification
            user.nin          = nin
            user.nin_verified = True
            user.save()

            return Response({
                'message':      'NIN verified successfully.',
                'nin_verified': user.nin_verified,
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BVNVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BVNVerificationSerializer(data=request.data)

        if serializer.is_valid():
            bvn  = serializer.validated_data['bvn']
            user = request.user

            # In production this is where you call Mono or Okra BVN API
            # For now we simulate a successful verification
            user.bvn          = bvn
            user.bvn_verified = True
            user.save()

            return Response({
                'message':      'BVN linked successfully.',
                'bvn_verified': user.bvn_verified,
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#KYC INFORMATION
class KYCStatusView(APIView):
    """
    Returns the user's current KYC status.
    The frontend uses this to show which tier
    the user is on and what they still need to do.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = KYCStatusSerializer(request.user)
        return Response(serializer.data)


class KYCTier1View(APIView):
    """
    User submits NIN to achieve Tier 1.
    Requirements: phone verified + NIN verified.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check phone is verified first
        if not request.user.phone_verified:
            return Response(
                {'error': 'You must verify your phone number before completing KYC Tier 1.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = KYCTier1Serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        nin  = serializer.validated_data['nin']
        user = request.user

        # Block re-verification with a different NIN
        if user.nin_verified and user.nin != nin:
            return Response(
                {'error': 'A different NIN is already verified on this account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # In production: call Prembly/Smile Identity here
        # For now: mock successful verification
        user.nin          = nin
        user.nin_verified = True
        user.upgrade_kyc_tier()

        return Response({
            'message':   'Tier 1 verification complete.',
            'kyc_tier':  user.kyc_tier,
            'unlocks':   ['Browse listings', 'View credit score', 'Basic payments'],
        })


class KYCTier2View(APIView):
    """
    User submits BVN + address to achieve Tier 2.
    Requirement: must already be Tier 1.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.kyc_tier < 1:
            return Response(
                {'error': 'You must complete Tier 1 before upgrading to Tier 2.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = KYCTier2Serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        data = serializer.validated_data

        # In production: call Mono/Okra BVN API here
        # For now: mock successful verification
        user.bvn           = data['bvn']
        user.bvn_verified  = True
        user.address_line1 = data['address_line1']
        user.address_line2 = data.get('address_line2', '')
        user.lga           = data['lga']
        user.state         = data['state']
        user.upgrade_kyc_tier()

        return Response({
            'message':  'Tier 2 verification complete.',
            'kyc_tier': user.kyc_tier,
            'unlocks':  ['Rent payments', 'Savings pockets', 'Credit building'],
        })


class KYCTier3View(APIView):
    """
    User submits income + NOK to achieve Tier 3.
    Requirement: must already be Tier 2.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.kyc_tier < 2:
            return Response(
                {'error': 'You must complete Tier 2 before upgrading to Tier 3.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = KYCTier3Serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        data = serializer.validated_data

        user.employer_name    = data['employer_name']
        user.monthly_income   = data['monthly_income']
        user.nok_name         = data['nok_name']
        user.nok_phone        = data['nok_phone']
        user.nok_relationship = data['nok_relationship']
        user.upgrade_kyc_tier()

        return Response({
            'message':  'Tier 3 verification complete.',
            'kyc_tier': user.kyc_tier,
            'unlocks':  ['Rent-to-own', 'BNPL options', 'Premium financing'],
        })