from rest_framework              import status
from rest_framework.views        import APIView
from rest_framework.response     import Response
from rest_framework.permissions  import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer, NINVerificationSerializer, BVNVerificationSerializer



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

