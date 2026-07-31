from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from datetime import datetime, date

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    AppointmentCancelSerializer,
    AppointmentRescheduleSerializer
)
from .services import (
    validate_and_book_appointment,
    cancel_appointment,
    reschedule_appointment
)
from apps.accounts.models import Patient

class AppointmentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        patient = getattr(request.user, 'patient_profile', None)
        if not patient:
            return Response({'error': 'Only registered patients can list appointments.'}, status=status.HTTP_403_FORBIDDEN)
        
        appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date', '-start_time')
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AppointmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get patient profile for logged-in user or from request data
        patient = getattr(request.user, 'patient_profile', None)
        if not patient and 'patient_id' in serializer.validated_data:
            patient = serializer.validated_data['patient_id']

        if not patient:
            return Response({'error': 'Patient profile required.'}, status=status.HTTP_400_BAD_REQUEST)

        doctor = serializer.validated_data['doctor']
        appointment_date = serializer.validated_data['appointment_date']
        start_time_obj = serializer.validated_data['start_time']

        try:
            appointment = validate_and_book_appointment(
                patient=patient,
                doctor=doctor,
                appointment_date=appointment_date,
                start_time_obj=start_time_obj
            )
            return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)
        except DjangoValidationError as e:
            return Response({'error': e.message if hasattr(e, 'message') else str(e.messages[0])}, status=status.HTTP_400_BAD_REQUEST)


class AppointmentCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        serializer = AppointmentCancelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reason = serializer.validated_data.get('reason', '')
        try:
            updated_appointment = cancel_appointment(appointment, reason=reason)
            return Response(AppointmentSerializer(updated_appointment).data, status=status.HTTP_200_OK)
        except DjangoValidationError as e:
            return Response({'error': e.message if hasattr(e, 'message') else str(e.messages[0])}, status=status.HTTP_400_BAD_REQUEST)


class AppointmentRescheduleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        serializer = AppointmentRescheduleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_date = serializer.validated_data['appointment_date']
        new_start_time = serializer.validated_data['start_time']

        try:
            updated_appointment = reschedule_appointment(
                appointment=appointment,
                new_date=new_date,
                new_start_time_obj=new_start_time
            )
            return Response(AppointmentSerializer(updated_appointment).data, status=status.HTTP_200_OK)
        except DjangoValidationError as e:
            return Response({'error': e.message if hasattr(e, 'message') else str(e.messages[0])}, status=status.HTTP_400_BAD_REQUEST)


class PatientAppointmentsView(APIView):
    """
    Bonus requirement: GET /patients/{id}/appointments — upcoming appointments sorted by date.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        today = date.today()
        upcoming = Appointment.objects.filter(
            patient=patient,
            appointment_date__gte=today,
            status=Appointment.STATUS_SCHEDULED
        ).order_by('appointment_date', 'start_time')

        serializer = AppointmentSerializer(upcoming, many=True)
        return Response(serializer.data)
