from rest_framework              import status
from rest_framework.views        import APIView
from rest_framework.response     import Response
from rest_framework.permissions  import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer



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