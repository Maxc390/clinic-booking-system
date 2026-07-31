from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.core.exceptions import ValidationError
from datetime import time, date, timedelta
from apps.doctors.models import Doctor, WorkingHours

class DoctorAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.doctor = Doctor.objects.create(
            first_name='Sarah',
            last_name='Jenkins',
            specialization='Cardiology',
            email='sarah@clinic.com',
            phone='+254700000001'
        )
        self.wh = WorkingHours.objects.create(
            doctor=self.doctor,
            day_of_week=0, # Mon
            start_time=time(8, 0),
            end_time=time(17, 0)
        )
        self.list_url = reverse('doctor-list')
        self.detail_url = reverse('doctor-detail', kwargs={'pk': self.doctor.id})
        self.avail_url = reverse('doctor-availability', kwargs={'pk': self.doctor.id})

    def test_doctor_str_and_properties(self):
        self.assertEqual(str(self.doctor), "Dr. Sarah Jenkins (Cardiology)")
        self.assertEqual(self.doctor.full_name, "Dr. Sarah Jenkins")
        self.assertIn("Monday", str(self.wh))

    def test_working_hours_max_12_hours_validation(self):
        invalid_wh = WorkingHours(
            doctor=self.doctor,
            day_of_week=1,
            start_time=time(7, 0),
            end_time=time(20, 0) # 13 hours
        )
        with self.assertRaises(ValidationError):
            invalid_wh.clean()

    def test_doctor_list_and_detail_api(self):
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

        res_detail = self.client.get(self.detail_url)
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data['specialization'], 'Cardiology')

    def test_doctor_availability_api(self):
        future_mon = date.today() + timedelta(days=7)
        while future_mon.weekday() != 0:
            future_mon += timedelta(days=1)

        res = self.client.get(f"{self.avail_url}?date={future_mon.strftime('%Y-%m-%d')}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('available_slots', res.data)
        self.assertTrue(len(res.data['available_slots']) > 0)

        # Invalid date format test
        res_err = self.client.get(f"{self.avail_url}?date=invalid-date")
        self.assertEqual(res_err.status_code, status.HTTP_400_BAD_REQUEST)
