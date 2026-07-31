from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date, time, timedelta

from apps.accounts.models import Patient
from apps.doctors.models import Doctor, WorkingHours
from apps.appointments.models import Appointment
from apps.appointments.services import (
    validate_and_book_appointment,
    cancel_appointment,
    reschedule_appointment,
    get_available_slots
)

class CancelAndRescheduleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testpatient', email='patient@test.com', password='password123')
        self.patient = Patient.objects.create(user=self.user)

        self.user2 = User.objects.create_user(username='patient2', email='patient2@test.com', password='password123')
        self.patient2 = Patient.objects.create(user=self.user2)

        self.doctor = Doctor.objects.create(
            first_name='Sarah', last_name='Jenkins', specialization='General Practice', email='sarah@clinic.com'
        )
        for day in range(5):
            WorkingHours.objects.create(
                doctor=self.doctor, day_of_week=day, start_time=time(8, 0), end_time=time(17, 0)
            )

        self.future_date = date.today() + timedelta(days=7)
        while self.future_date.weekday() > 4:
            self.future_date += timedelta(days=1)

    def test_cancel_frees_slot_for_others(self):
        # Patient 1 books 09:00 slot
        appt = validate_and_book_appointment(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.future_date,
            start_time_obj=time(9, 0)
        )

        # Cancel appointment
        cancel_appointment(appt, reason="Conflict")
        self.assertEqual(appt.status, Appointment.STATUS_CANCELLED)
        self.assertEqual(appt.cancel_reason, "Conflict")

        # Now Patient 2 can book the exact same slot!
        appt2 = validate_and_book_appointment(
            patient=self.patient2,
            doctor=self.doctor,
            appointment_date=self.future_date,
            start_time_obj=time(9, 0)
        )
        self.assertEqual(appt2.status, Appointment.STATUS_SCHEDULED)

    def test_cannot_cancel_twice(self):
        appt = validate_and_book_appointment(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.future_date,
            start_time_obj=time(9, 0)
        )
        cancel_appointment(appt, reason="First cancel")

        with self.assertRaises(ValidationError) as ctx:
            cancel_appointment(appt, reason="Second cancel")
        self.assertIn("already cancelled", str(ctx.exception))

    def test_reschedule_appointment(self):
        appt = validate_and_book_appointment(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.future_date,
            start_time_obj=time(9, 0)
        )

        # Reschedule to 11:00
        reschedule_appointment(appt, new_date=self.future_date, new_start_time_obj=time(11, 0))
        self.assertEqual(appt.start_time, time(11, 0))

        # 09:00 slot should now be free for Patient 2!
        appt2 = validate_and_book_appointment(
            patient=self.patient2,
            doctor=self.doctor,
            appointment_date=self.future_date,
            start_time_obj=time(9, 0)
        )
        self.assertEqual(appt2.status, Appointment.STATUS_SCHEDULED)

    def test_cannot_reschedule_cancelled_appointment(self):
        appt = validate_and_book_appointment(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.future_date,
            start_time_obj=time(9, 0)
        )
        cancel_appointment(appt)

        with self.assertRaises(ValidationError) as ctx:
            reschedule_appointment(appt, new_date=self.future_date, new_start_time_obj=time(11, 0))
        self.assertIn("Cannot reschedule", str(ctx.exception))
