from django.test import TestCase
from django.urls import reverse
from .models import User
from locations.models import County

class AuthenticationTests(TestCase):
    def setUp(self):
        self.county=County.objects.create(name="Test County",code="T01")
        self.officer=User.objects.create_user("officer",password="StrongPass!789",role="officer",county=self.county)
        self.team=User.objects.create_user("team",password="StrongPass!789",role="team_member",county=self.county)
    def test_login(self):
        response=self.client.post(reverse("accounts:login"),{"username":"officer","password":"StrongPass!789"}); self.assertRedirects(response,reverse("dashboard:home"),fetch_redirect_response=False)
    def test_anonymous_dashboard_redirects_to_login(self):
        response=self.client.get(reverse("dashboard:county")); self.assertEqual(response.status_code,302); self.assertIn(reverse("accounts:login"),response.url)
    def test_team_member_cannot_access_county_dashboard(self):
        self.client.force_login(self.team); self.assertEqual(self.client.get(reverse("dashboard:county")).status_code,403)
    def test_officer_can_access_county_dashboard(self):
        self.client.force_login(self.officer); self.assertEqual(self.client.get(reverse("dashboard:county")).status_code,200)
    def test_username_with_spaces_can_be_created_and_used_to_login(self):
        user=User.objects.create_superuser("  Japhes   Murithi  ","japhes@example.invalid","AnotherStrong!789")
        self.assertEqual(user.username,"Japhes Murithi")
        self.assertTrue(self.client.login(username="Japhes Murithi",password="AnotherStrong!789"))
