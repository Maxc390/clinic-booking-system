from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.accounts.models import Patient

class AuthAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('auth-register')
        self.login_url = reverse('auth-login')
        self.logout_url = reverse('auth-logout')
        self.profile_url = reverse('auth-profile')

    def test_register_success(self):
        payload = {
            'username': 'newpatient',
            'email': 'new@patient.com',
            'password': 'password123',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'phone': '+254700111222',
            'date_of_birth': '1995-05-15'
        }
        res = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', res.data)
        self.assertEqual(Patient.objects.count(), 1)
        patient = Patient.objects.first()
        self.assertEqual(str(patient), "Jane Doe (new@patient.com)")
        self.assertEqual(patient.full_name, "Jane Doe")
        self.assertEqual(patient.email, "new@patient.com")

    def test_register_duplicate_username_and_email(self):
        User.objects.create_user(username='newpatient', email='new@patient.com', password='password123')
        payload = {
            'username': 'newpatient',
            'email': 'new@patient.com',
            'password': 'password123'
        }
        res = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success_and_failure(self):
        user = User.objects.create_user(username='loginuser', email='login@test.com', password='secretpassword')
        Patient.objects.create(user=user)

        # Failure
        res = self.client.post(self.login_url, {'username': 'loginuser', 'password': 'wrongpassword'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Success
        res = self.client.post(self.login_url, {'username': 'loginuser', 'password': 'secretpassword'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('token', res.data)

    def test_logout_and_profile_authenticated(self):
        user = User.objects.create_user(username='profileuser', email='profile@test.com', password='secretpassword')
        patient = Patient.objects.create(user=user)
        self.client.force_authenticate(user=user)

        # Profile check
        res = self.client.get(self.profile_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['email'], 'profile@test.com')

        # Logout check
        res = self.client.post(self.logout_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_profile_unauthenticated(self):
        res = self.client.get(self.profile_url)
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
