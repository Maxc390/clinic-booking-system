from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from datetime import date, time, timedelta

from apps.accounts.models import Patient
from apps.doctors.models import Doctor, WorkingHours
from apps.appointments.models import Appointment

class AppointmentAPIViewsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='apiuser', email='api@test.com', password='password123')
        self.patient = Patient.objects.create(user=self.user)
        self.doctor = Doctor.objects.create(
            first_name='Amina', last_name='Hassan', specialization='Pediatrics', email='amina@clinic.com'
        )
        for day in range(7):
            WorkingHours.objects.create(
                doctor=self.doctor, day_of_week=day, start_time=time(8, 0), end_time=time(18, 0)
            )

        self.future_date = date.today() + timedelta(days=5)
        self.list_create_url = reverse('appointment-list-create')
        self.patient_appts_url = reverse('patient-appointments', kwargs={'pk': self.patient.id})

    def test_unauthenticated_access_denied(self):
        res = self.client.get(self.list_create_url)
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_authenticated_booking_via_api(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            'patient_id': str(self.patient.id),
            'doctor_id': str(self.doctor.id),
            'appointment_date': self.future_date.strftime('%Y-%m-%d'),
            'start_time': '10:00'
        }
        res = self.client.post(self.list_create_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.count(), 1)
        appt_id = res.data['id']

        # List appointments
        res_list = self.client.get(self.list_create_url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_list.data), 1)

        # Cancel appointment via API
        cancel_url = reverse('appointment-cancel', kwargs={'pk': appt_id})
        res_cancel = self.client.patch(cancel_url, {'reason': 'Patient emergency'}, format='json')
        self.assertEqual(res_cancel.status_code, status.HTTP_200_OK)
        self.assertEqual(res_cancel.data['status'], 'cancelled')

        # Reschedule cancelled appointment error test
        reschedule_url = reverse('appointment-reschedule', kwargs={'pk': appt_id})
        res_resched = self.client.patch(reschedule_url, {
            'appointment_date': self.future_date.strftime('%Y-%m-%d'),
            'start_time': '14:00'
        }, format='json')
        self.assertEqual(res_resched.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reschedule_success_via_api(self):
        self.client.force_authenticate(user=self.user)
        appt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.future_date,
            start_time=time(10, 0),
            status=Appointment.STATUS_SCHEDULED
        )
        reschedule_url = reverse('appointment-reschedule', kwargs={'pk': appt.id})
        res = self.client.patch(reschedule_url, {
            'appointment_date': self.future_date.strftime('%Y-%m-%d'),
            'start_time': '11:30'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['start_time'], '11:30')

    def test_bonus_patient_appointments_api(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.future_date,
            start_time=time(14, 0),
            status=Appointment.STATUS_SCHEDULED
        )
        res = self.client.get(self.patient_appts_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
