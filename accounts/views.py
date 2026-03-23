from rest_framework              import status
from rest_framework.views        import APIView
from rest_framework.response     import Response
from rest_framework.permissions  import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth.hashers import make_password, check_password
import uuid

from .models import User, UserProfile, DeviceSession, ReferralCredit
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    BasicUserSerializer,
    BVNVerificationSerializer,
    NINVerificationSerializer,
    KYCTier1Serializer,
    KYCTier2Serializer,
    KYCTier3Serializer,
    KYCStatusSerializer,
    ProfilePhotoSerializer,
    ProfileCompletionSerializer,
    ExtendedProfileSerializer,
    SetPINSerializer,
    PINLoginSerializer,
    DeviceSessionSerializer,
    ReferralCreditSerializer,
    ReferralDashboardSerializer,
)
from .services import ReferralService


# ── Helper ─────────────────────────────────────────────────────────────────

def _tokens_for_user(user):
    """
    Generates access and refresh JWT tokens
    for a given user. Used by login and PIN login.
    """
    refresh = RefreshToken.for_user(user)
    return {
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
    }


# ══════════════════════════════════════════════════════════════════════════
# AUTH VIEWS
# ══════════════════════════════════════════════════════════════════════════

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
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            return Response({
                'message': 'Login successful.',
                'tokens':  _tokens_for_user(user),
                'user': {
                    'phone':      user.phone,
                    'first_name': user.first_name,
                    'last_name':  user.last_name,
                    'role':       user.role,
                    'kyc_tier':   user.kyc_tier,
                }
            })
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully.'})
        
        except TokenError:
            return Response(
                {'error': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ══════════════════════════════════════════════════════════════════════════
# PROFILE VIEWS
# ══════════════════════════════════════════════════════════════════════════

class ProfileView(APIView):
    """
    GET — returns basic user info and KYC status.
    This is the lightweight profile used after
    login and on app boot.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = BasicUserSerializer(request.user)
        return Response(serializer.data)


class ProfileBuilderView(APIView):
    """
    GET  — returns extended profile data
           (employment, emergency contact, referees)
           plus completion score.
    PATCH — updates any extended profile field.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user
        )
        serializer = ExtendedProfileSerializer(profile)
        return Response({
            'completion_score': profile.completion_score(),
            'profile':          serializer.data,
        })

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user
        )
        serializer = ExtendedProfileSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message':          'Profile updated.',
                'completion_score': profile.completion_score(),
                'profile':          serializer.data,
            })
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class ProfileCompletionView(APIView):
    """
    GET — returns the full completion breakdown
    showing each section, whether it is complete,
    and how many points it is worth.
    Drives the progress bar on the frontend.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileCompletionSerializer(
            request.user,
            context={'request': request},
        )
        return Response(serializer.data)


class ProfilePhotoView(APIView):
    """
    POST — upload or replace profile photo.
    Send as multipart/form-data not JSON.
    Key: profile_photo, Value: image file.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProfilePhotoSerializer(
            request.user,
            data=request.data,
        )
        if serializer.is_valid():
            serializer.save()
            # Trigger completion score recalculation
            profile, _ = UserProfile.objects.get_or_create(
                user=request.user
            )
            profile.save()
            return Response({
                'message':    'Profile photo uploaded.',
                'photo_url':  request.build_absolute_uri(
                    request.user.profile_photo.url
                ),
                'completion': profile.completion_score(),
            })
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


# ══════════════════════════════════════════════════════════════════════════
# IDENTITY VERIFICATION VIEWS
# ══════════════════════════════════════════════════════════════════════════

class BVNVerificationView(APIView):
    """
    POST — submits BVN for standalone verification.
    Note: BVN is also collected during KYCTier2View.
    This endpoint is for users who want to link
    BVN separately outside the KYC tier flow.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BVNVerificationSerializer(data=request.data)
       
        if serializer.is_valid():
            user          = request.user
            user.bvn      = serializer.validated_data['bvn']
            user.bvn_verified = True
            user.save()
           
            return Response({
                'message':      'BVN linked successfully.',
                'bvn_verified': user.bvn_verified,
            })
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )
    
class NINVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = NINVerificationSerializer(data=request.data)

        if serializer.is_valid():
            nin  = serializer.validated_data['nin']
            user = request.user

            # In production this is where NIMC is called or Smile Identity API
            # For now we simulate a successful verification
            user.nin          = nin
            user.nin_verified = True
            user.save()

            return Response({
                'message':      'NIN verified successfully.',
                'nin_verified': user.nin_verified,
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════════════════════════
# KYC VIEWS
# ══════════════════════════════════════════════════════════════════════════

# Referral points awarded for each credit type and referral level
class KYCStatusView(APIView):
    """
    GET — returns current KYC tier, what is
    verified, and what tier the user qualifies for.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = KYCStatusSerializer(request.user)
        return Response(serializer.data)


class KYCTier1View(APIView):
    """
    POST — user submits NIN to achieve Tier 1.
    Requirements: phone must be verified first.
    Unlocks: browse listings, credit score, basic payments.
    In production: replace mock with Prembly API call.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        if not request.user.phone_verified:
            return Response(
                {'error': 'You must verify your phone before completing KYC Tier 1.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = KYCTier1Serializer(data=request.data)
       
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        nin  = serializer.validated_data['nin']
        user = request.user


        if user.nin_verified and user.nin != nin:
            return Response(
                {'error': 'A different NIN is already verified on this account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save first, then refresh, then upgrade tier
        user.nin          = nin
        user.nin_verified = True
        user.save()
        user.refresh_from_db()
        user.upgrade_kyc_tier()

        return Response({
            'message':  'Tier 1 verification complete.',
            'kyc_tier': user.kyc_tier,
            'unlocks':  [
                'Browse listings',
                'View credit score',
                'Basic payments',
            ],
        })


class KYCTier2View(APIView):
    """
    POST — user submits BVN + address to achieve Tier 2.
    Requirements: must already be Tier 1.
    Unlocks: rent payments, savings pockets, credit building.
    In production: replace mock with Mono API call.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.kyc_tier < 1:
            return Response(
                {'error': 'You must complete Tier 1 before upgrading to Tier 2.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = KYCTier2Serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        data = serializer.validated_data

        # Save first, then refresh, then upgrade tier
        user.bvn           = data['bvn']
        user.bvn_verified  = True
        user.address_line1 = data['address_line1']
        user.address_line2 = data.get('address_line2', '')
        user.lga           = data['lga']
        user.state         = data['state']
        user.save()
        user.refresh_from_db()
        user.upgrade_kyc_tier()

        return Response({
            'message':  'Tier 2 verification complete.',
            'kyc_tier': user.kyc_tier,
            'unlocks':  [
                'Rent payments',
                'Savings pockets',
                'Credit building',
            ],
        })


class KYCTier3View(APIView):
    """
    POST — user submits income + NOK to achieve Tier 3.
    Requirements: must already be Tier 2.
    Unlocks: rent-to-own, BNPL, premium financing.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.kyc_tier < 2:
            return Response(
                {'error': 'You must complete Tier 2 before upgrading to Tier 3.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = KYCTier3Serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        data = serializer.validated_data

        # Save first, then refresh, then upgrade tier
        user.employer_name    = data['employer_name']
        user.monthly_income   = data['monthly_income']
        user.nok_name         = data['nok_name']
        user.nok_phone        = data['nok_phone']
        user.nok_relationship = data['nok_relationship']
        user.save()
        user.refresh_from_db()
        user.upgrade_kyc_tier()

        return Response({
            'message':  'Tier 3 verification complete.',
            'kyc_tier': user.kyc_tier,
            'unlocks':  [
                'Rent-to-own',
                'BNPL options',
                'Premium financing',
            ],
        })


# ══════════════════════════════════════════════════════════════════════════
# PIN & DEVICE VIEWS
# ══════════════════════════════════════════════════════════════════════════

class SetPINView(APIView):
    """
    POST — sets a 4-6 digit PIN and registers
    the device. Returns a device_token the
    mobile app must store locally.
    PIN is hashed before storage — never stored
    in plaintext.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SetPINSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        user        = request.user
        pin         = serializer.validated_data['pin']
        device_name = serializer.validated_data.get(
            'device_name', 'Unknown Device'
        )
        platform    = serializer.validated_data.get('platform', 'android')

        # Hash and store PIN
        user.pin_hash = make_password(pin)
        user.pin_set  = True
        user.save(update_fields=['pin_hash', 'pin_set'])

        # Generate unique device token
        device_token = str(uuid.uuid4()).replace('-', '')

        DeviceSession.objects.create(
            user         = user,
            device_token = device_token,
            device_name  = device_name,
            platform     = platform,
            ip_address   = request.META.get('REMOTE_ADDR'),
        )

        return Response({
            'message':      'PIN set successfully.',
            'device_token': device_token,
        })


class PINLoginView(APIView):
    """
    POST — login using phone + PIN + device_token.
    No password required once PIN is set.
    The device_token is issued by SetPINView and
    stored locally on the mobile device.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PINLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone        = serializer.validated_data['phone']
        pin          = serializer.validated_data['pin']
        device_token = serializer.validated_data['device_token']

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.pin_set:
            return Response(
                {'error': 'PIN not set. Please log in with password first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify the device token is registered and active
        try:
            device = DeviceSession.objects.get(
                user         = user,
                device_token = device_token,
                is_active    = True,
            )
        except DeviceSession.DoesNotExist:
            return Response(
                {'error': 'Unrecognised device. Please log in with password first.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Verify PIN against stored hash
        if not check_password(pin, user.pin_hash):
            return Response(
                {'error': 'Incorrect PIN.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        
        return Response({
            'message': 'PIN login successful.',
            'tokens':  _tokens_for_user(user),
            'user': {
                'phone':      user.phone,
                'first_name': user.first_name,
                'last_name':  user.last_name,
                'role':       user.role,
                'kyc_tier':   user.kyc_tier,
            },
        })


class DeviceListView(APIView):
    """
    GET — lists all trusted devices on the
    current user's account.
    Useful for a 'Manage devices' screen.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        devices    = DeviceSession.objects.filter(user=request.user)
        serializer = DeviceSessionSerializer(devices, many=True)
        return Response(serializer.data)


class DeviceRevokeView(APIView):
    """
    POST — deactivates a specific device token.
    The device can no longer use PIN login.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            device = DeviceSession.objects.get(
                pk   = pk,
                user = request.user,
            )
        except DeviceSession.DoesNotExist:
            return Response(
                {'error': 'Device not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        device.is_active = False
        device.save(update_fields=['is_active'])

        return Response({'message': 'Device revoked successfully.'})


# ══════════════════════════════════════════════════════════════════════════
# REFERRAL VIEWS
# ══════════════════════════════════════════════════════════════════════════

class ReferralDashboardView(APIView):
    """
    GET — returns the user's referral code,
    full downline tree, total points earned,
    and level breakdown.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        total_points     = sum(
            c.points for c in user.referral_credits.all()
        )
        direct_count     = user.direct_referrals.count()
        tree             = ReferralService.get_referral_tree(user)

        def count_nodes(nodes):
            count = len(nodes)
            for node in nodes:
                count += count_nodes(node.get('downline', []))
            return count

        return Response({
            'referral_code':    user.referral_code,
            'referral_link':    f'https://kredhaus.app/join/{user.referral_code}',
            'total_referrals':  count_nodes(tree),
            'direct_referrals': direct_count,
            'total_points':     total_points,
            'tree':             tree,
        })


class ReferralCreditHistoryView(APIView):
    """
    GET — lists every credit event earned
    by the current user through the referral tree.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        credits    = ReferralCredit.objects.filter(
            beneficiary=request.user
        )
        serializer = ReferralCreditSerializer(credits, many=True)
        total      = sum(c.points for c in credits)
        return Response({
            'total_points': total,
            'credits':      serializer.data,
        })