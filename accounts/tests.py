from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_and_login(self):
        res = self.client.post("/api/auth/register/", {
            "email": "test@example.com",
            "username": "testuser",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["email"], "test@example.com")

        res = self.client.post("/api/auth/login/", {
            "email": "test@example.com",
            "password": "StrongPass123!",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_register_password_mismatch(self):
        res = self.client.post("/api/auth/register/", {
            "email": "test@example.com",
            "username": "testuser",
            "password": "StrongPass123!",
            "password_confirm": "WrongPass456!",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_requires_auth(self):
        res = self.client.get("/api/auth/profile/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_with_auth(self):
        User.objects.create_user(
            email="auth@test.com", username="authuser", password="Pass1234!"
        )
        login_res = self.client.post("/api/auth/login/", {
            "email": "auth@test.com",
            "password": "Pass1234!",
        })
        token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        res = self.client.get("/api/auth/profile/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], "auth@test.com")
