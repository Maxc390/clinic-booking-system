from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date, time, datetime, timedelta

from apps.accounts.models import Patient
from apps.doctors.models import Doctor, WorkingHours
from apps.appointments.models import Appointment
from apps.appointments.services import validate_and_book_appointment, get_available_slots

class BookingLogicTests(TestCase):
    def setUp(self):
        # Create Patient
        self.user = User.objects.create_user(username='testpatient', email='patient@test.com', password='password123')
        self.patient = Patient.objects.create(user=self.user, phone='+254711111111')

        # Create 2nd Patient for double-booking test
        self.user2 = User.objects.create_user(username='patient2', email='patient2@test.com', password='password123')
        self.patient2 = Patient.objects.create(user=self.user2)

        # Create Doctor 1 (Works Mon-Fri 08:00 to 17:00)
        self.doctor1 = Doctor.objects.create(
            first_name='John', last_name='Doe', specialization='General Practice', email='johndoe@clinic.com'
        )
        for day in range(5): # Mon-Fri
            WorkingHours.objects.create(
                doctor=self.doctor1, day_of_week=day, start_time=time(8, 0), end_time=time(17, 0)
            )

        # Create Doctor 2
        self.doctor2 = Doctor.objects.create(
            first_name='Jane', last_name='Smith', specialization='Pediatrics', email='janesmith@clinic.com'
        )
        for day in range(5):
            WorkingHours.objects.create(
                doctor=self.doctor2, day_of_week=day, start_time=time(9, 0), end_time=time(17, 0)
            )

        # Target booking date = 7 days in future (always valid future day)
        self.future_date = date.today() + timedelta(days=7)
        # Ensure future_date is a weekday (0-4)
        while self.future_date.weekday() > 4:
            self.future_date += timedelta(days=1)

    def test_successful_booking(self):
        appt = validate_and_book_appointment(
            patient=self.patient,
            doctor=self.doctor1,
            appointment_date=self.future_date,
            start_time_obj=time(9, 0)
        )
        self.assertEqual(appt.status, Appointment.STATUS_SCHEDULED)
        self.assertEqual(appt.end_time, time(9, 30))

    def test_prevent_double_booking_same_slot(self):
        # First booking succeeds
        validate_and_book_appointment(
            patient=self.patient,
            doctor=self.doctor1,
            appointment_date=self.future_date,
            start_time_obj=time(10, 0)
        )

        # Second booking for same doctor, same date, same time should fail
        with self.assertRaises(ValidationError) as ctx:
            validate_and_book_appointment(
                patient=self.patient2,
                doctor=self.doctor1,
                appointment_date=self.future_date,
                start_time_obj=time(10, 0)
            )
        self.assertIn("already taken", str(ctx.exception))

    def test_prevent_patient_multiple_appointments_same_day(self):
        # Patient books Doctor 1 at 09:00
        validate_and_book_appointment(
            patient=self.patient,
            doctor=self.doctor1,
            appointment_date=self.future_date,
            start_time_obj=time(9, 0)
        )

        # Same patient tries to book Doctor 2 at 11:00 on same day -> Should fail
        with self.assertRaises(ValidationError) as ctx:
            validate_and_book_appointment(
                patient=self.patient,
                doctor=self.doctor2,
                appointment_date=self.future_date,
                start_time_obj=time(11, 0)
            )
        self.assertIn("already has an active appointment", str(ctx.exception))

    def test_prevent_past_date_booking(self):
        past_date = date.today() - timedelta(days=1)
        with self.assertRaises(ValidationError) as ctx:
            validate_and_book_appointment(
                patient=self.patient,
                doctor=self.doctor1,
                appointment_date=past_date,
                start_time_obj=time(10, 0)
            )
        self.assertIn("past or within 1 hour", str(ctx.exception))

    def test_prevent_non_30min_slot(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_and_book_appointment(
                patient=self.patient,
                doctor=self.doctor1,
                appointment_date=self.future_date,
                start_time_obj=time(9, 15)
            )
        self.assertIn("30-minute slots", str(ctx.exception))

    def test_prevent_outside_working_hours(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_and_book_appointment(
                patient=self.patient,
                doctor=self.doctor1,
                appointment_date=self.future_date,
                start_time_obj=time(18, 0)
            )
        self.assertIn("outside the doctor's working hours", str(ctx.exception))
