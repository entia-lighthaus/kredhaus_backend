from rest_framework              import status
from rest_framework.views        import APIView
from rest_framework.response     import Response
from rest_framework.permissions  import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth.hashers import make_password, check_password
from .models import User, Referee, TrustedDevice
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserProfileSerializer,
    NINVerificationSerializer,
    BVNVerificationSerializer,
    KYCTier1Serializer,
    KYCTier2Serializer,
    KYCTier3Serializer,
    KYCStatusSerializer,
    RefereeSerializer,
    EmergencyContactSerializer,
    ProfilePhotoSerializer,
    ProfileCompletionSerializer,
    SetPINSerializer,
    PINLoginSerializer,
)

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

    # User submits NIN to achieve Tier 1 ...Requirements: phone verified + NIN verified.
    
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
        user.save()

        user.refresh_from_db()
        user.upgrade_kyc_tier()

        return Response({
            'message':  'Tier 2 verification complete.',
            'kyc_tier': user.kyc_tier,
            'unlocks':  ['Rent payments', 'Savings pockets', 'Credit building'],
            'debug': {
            'phone_verified': user.phone_verified,
            'nin_verified':   user.nin_verified,
            'bvn_verified':   user.bvn_verified,
            'address_line1':  user.address_line1,
            'nok_name':       user.nok_name,
            'monthly_income': str(user.monthly_income),}
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
    

# Profile Completion Methods
# 
class ProfileCompletionView(APIView):
    """
    GET — Returns full profile completion
          breakdown and current score.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileCompletionSerializer(request.user)
        return Response(serializer.data)


class ProfilePhotoView(APIView):
    """
    POST — Upload or replace profile photo.
    Accepts multipart/form-data not JSON.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProfilePhotoSerializer(
            request.user,
            data=request.data,
        )
        if serializer.is_valid():
            serializer.save()
            request.user.calculate_profile_completion()
            return Response({
                'message':     'Profile photo uploaded.',
                'photo_url':   request.build_absolute_uri(
                    request.user.profile_photo.url
                ),
                'completion':  request.user.profile_completion,
            })
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class EmergencyContactView(APIView):
    """
    POST — Add or update emergency contact.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EmergencyContactSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user.emergency_name         = serializer.validated_data['emergency_name']
            user.emergency_phone        = serializer.validated_data['emergency_phone']
            user.emergency_relationship = serializer.validated_data['emergency_relationship']
            user.save()
            user.calculate_profile_completion()
            return Response({
                'message':    'Emergency contact saved.',
                'completion': user.profile_completion,
            })
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class RefereeListCreateView(APIView):
    """
    GET  — List all referees for the current user
    POST — Add a referee (max 2)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        referees   = request.user.referees.all()
        serializer = RefereeSerializer(referees, many=True)
        return Response(serializer.data)

    def post(self, request):
        if request.user.referees.count() >= 2:
            return Response(
                {'error': 'Maximum of 2 referees allowed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = RefereeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            request.user.calculate_profile_completion()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )
    

# These views handles security in accessing the Kredhaus app on devices.
# It uses pin codes to enter th app
class SetPINView(APIView):
    """
    POST — User sets a 4-6 digit PIN for quick login.
    PIN is hashed before storage.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SetPINSerializer(data=request.data)
        if serializer.is_valid():
            user          = request.user
            user.pin_hash = make_password(
                serializer.validated_data['pin']
            )
            user.pin_set  = True
            user.save(update_fields=['pin_hash', 'pin_set'])
            return Response({'message': 'PIN set successfully.'})
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class PINLoginView(APIView):
    """
    POST — Login with PIN instead of password.
    Only works from a registered trusted device.
    Device must have logged in with password at least once.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PINLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone     = serializer.validated_data['phone']
        pin       = serializer.validated_data['pin']
        device_id = serializer.validated_data['device_id']

        if phone.startswith('0'):
            phone = '+234' + phone[1:]

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

        # Check device is registered
        device = TrustedDevice.objects.filter(
            user=user,
            device_id=device_id,
        ).first()

        if not device:
            return Response(
                {'error': 'Unrecognised device. Please log in with password first.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not check_password(pin, user.pin_hash):
            return Response(
                {'error': 'Incorrect PIN.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Update device trust score
        device.trust_score = min(device.trust_score + 1, 100)
        device.save(update_fields=['trust_score', 'last_seen'])

        return Response({
            'message': 'PIN login successful.',
            'tokens':  _tokens_for_user(user),
            'user': {
                'phone':      user.phone,
                'first_name': user.first_name,
                'role':       user.role,
            }
        })


class RegisterDeviceView(APIView):
    """
    POST — Register a device after successful
    password login. Required before PIN login works.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device_id   = request.data.get('device_id')
        device_name = request.data.get('device_name', '')
        platform    = request.data.get('platform', 'android')

        if not device_id:
            return Response(
                {'error': 'device_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device, created = TrustedDevice.objects.get_or_create(
            user=request.user,
            device_id=device_id,
            defaults={
                'device_name': device_name,
                'platform':    platform,
                'is_trusted':  True,
                'trust_score': 10,
            }
        )

        return Response({
            'message':    'Device registered.' if created else 'Device already registered.',
            'device_id':  device.device_id,
            'is_trusted': device.is_trusted,
            'trust_score': device.trust_score,
        })