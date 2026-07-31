from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date, time, timedelta
from apps.accounts.models import Patient
from apps.doctors.models import Doctor, WorkingHours
from apps.appointments.models import Appointment

class FrontendViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='webuser', email='web@test.com', password='password123')
        self.patient = Patient.objects.create(user=self.user)
        self.doctor = Doctor.objects.create(
            first_name='David', last_name='Kipchirchir', specialization='Emergency', email='david@clinic.com'
        )
        for day in range(7):
            WorkingHours.objects.create(
                doctor=self.doctor, day_of_week=day, start_time=time(8, 0), end_time=time(18, 0)
            )

        self.future_date = date.today() + timedelta(days=5)

    def test_index_unauthenticated_and_authenticated(self):
        res = self.client.get(reverse('frontend-index'))
        self.assertEqual(res.status_code, 200)

        self.client.login(username='webuser', password='password123')
        res_auth = self.client.get(reverse('frontend-index'))
        self.assertEqual(res_auth.status_code, 302) # Redirects to dashboard

    def test_login_and_register_actions(self):
        # Login
        res_login = self.client.post(reverse('frontend-login'), {
            'username': 'webuser',
            'password': 'password123'
        })
        self.assertRedirects(res_login, reverse('frontend-dashboard'))

        # Register
        res_reg = self.client.post(reverse('frontend-register'), {
            'username': 'brandnewuser',
            'email': 'brandnew@test.com',
            'password': 'password123',
            'first_name': 'Brand',
            'last_name': 'New'
        })
        self.assertRedirects(res_reg, reverse('frontend-dashboard'))

        # Logout
        res_logout = self.client.get(reverse('frontend-logout'))
        self.assertRedirects(res_logout, reverse('frontend-index'))

    def test_dashboard_and_booking_page(self):
        self.client.login(username='webuser', password='password123')
        res_dash = self.client.get(reverse('frontend-dashboard'))
        self.assertEqual(res_dash.status_code, 200)

        res_book_get = self.client.get(reverse('frontend-book'))
        self.assertEqual(res_book_get.status_code, 200)

        # POST book
        res_book_post = self.client.post(reverse('frontend-book'), {
            'doctor_id': str(self.doctor.id),
            'appointment_date': self.future_date.strftime('%Y-%m-%d'),
            'slot_time': '10:00'
        })
        self.assertRedirects(res_book_post, reverse('frontend-dashboard'))
        self.assertEqual(Appointment.objects.count(), 1)

    def test_slot_picker_partial_htmx(self):
        url = reverse('frontend-slots-picker')
        res = self.client.get(f"{url}?doctor_id={self.doctor.id}&date={self.future_date.strftime('%Y-%m-%d')}")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '10:00')

    def test_cancel_and_reschedule_frontend_actions(self):
        self.client.login(username='webuser', password='password123')
        appt = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.future_date,
            start_time=time(10, 0),
            status=Appointment.STATUS_SCHEDULED
        )

        # Cancel
        res_cancel = self.client.post(reverse('frontend-cancel', kwargs={'pk': appt.id}), {
            'reason': 'Patient reason'
        })
        self.assertRedirects(res_cancel, reverse('frontend-dashboard'))
        appt.refresh_from_db()
        self.assertEqual(appt.status, 'cancelled')

        # Reschedule another appt
        appt2 = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.future_date,
            start_time=time(11, 0),
            status=Appointment.STATUS_SCHEDULED
        )
        res_resched = self.client.post(reverse('frontend-reschedule', kwargs={'pk': appt2.id}), {
            'appointment_date': self.future_date.strftime('%Y-%m-%d'),
            'slot_time': '15:00'
        })
        self.assertRedirects(res_resched, reverse('frontend-dashboard'))
        appt2.refresh_from_db()
        self.assertEqual(appt2.start_time, time(15, 0))
