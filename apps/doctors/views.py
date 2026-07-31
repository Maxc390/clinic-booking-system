from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from datetime import datetime, date

from .models import Doctor
from .serializers import DoctorSerializer
from apps.appointments.services import get_available_slots

class DoctorListView(generics.ListAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

class DoctorDetailView(generics.RetrieveAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [permissions.AllowAny]

class DoctorAvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        doctor = get_object_or_404(Doctor, pk=pk)
        date_str = request.query_params.get('date')

        if not date_str:
            target_date = date.today()
        else:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        available_slots = get_available_slots(doctor, target_date)
        return Response({
            'doctor_id': str(doctor.id),
            'doctor_name': doctor.full_name,
            'date': target_date.strftime('%Y-%m-%d'),
            'available_slots': available_slots
        })
