from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout

from .serializers import RegisterSerializer, LoginSerializer, PatientSerializer
from .models import Patient

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            patient = serializer.save()
            token, _ = Token.objects.get_or_create(user=patient.user)
            return Response({
                'message': 'Registration successful.',
                'token': token.key,
                'patient': PatientSerializer(patient).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
            if user:
                login(request, user)
                token, _ = Token.objects.get_or_create(user=user)
                patient = getattr(user, 'patient_profile', None)
                patient_data = PatientSerializer(patient).data if patient else None
                return Response({
                    'message': 'Login successful.',
                    'token': token.key,
                    'patient': patient_data
                }, status=status.HTTP_200_OK)
            return Response({'error': 'Invalid username or password.'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        logout(request)
        return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        patient = getattr(request.user, 'patient_profile', None)
        if not patient:
            return Response({'error': 'User is not registered as a patient.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PatientSerializer(patient).data)
