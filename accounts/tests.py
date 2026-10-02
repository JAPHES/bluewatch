import secrets
from django.test import TestCase
from django.urls import reverse
from .models import User
from locations.models import County

class AuthenticationTests(TestCase):
    def setUp(self):
        self.password=secrets.token_urlsafe(32)
        self.county=County.objects.create(name="Test County",code="T01")
        self.officer=User.objects.create_user("officer",password=self.password,role="officer",county=self.county)
        self.team=User.objects.create_user("team",password=self.password,role="team_member",county=self.county)
    def test_login(self):
        response=self.client.post(reverse("accounts:login"),{"username":"officer","password":self.password}); self.assertRedirects(response,reverse("dashboard:home"),fetch_redirect_response=False)
    def test_anonymous_dashboard_redirects_to_login(self):
        response=self.client.get(reverse("dashboard:county")); self.assertEqual(response.status_code,302); self.assertIn(reverse("accounts:login"),response.url)
    def test_team_member_cannot_access_county_dashboard(self):
        self.client.force_login(self.team); self.assertEqual(self.client.get(reverse("dashboard:county")).status_code,403)
    def test_officer_can_access_county_dashboard(self):
        self.client.force_login(self.officer); self.assertEqual(self.client.get(reverse("dashboard:county")).status_code,200)
    def test_username_with_spaces_can_be_created_and_used_to_login(self):
        password=secrets.token_urlsafe(32)
        user=User.objects.create_superuser("  Japhes   Murithi  ","japhes@example.invalid",password)
        self.assertEqual(user.username,"Japhes Murithi")
        self.assertTrue(self.client.login(username="Japhes Murithi",password=password))


class StaffCreationTests(TestCase):
    def setUp(self):
        self.county = County.objects.create(name="Mombasa", code="001")
        self.other_county = County.objects.create(name="Kilifi", code="003")
        self.admin = User.objects.create_user(
            "county.admin", password=secrets.token_urlsafe(32),
            role=User.Role.COUNTY_ADMIN, county=self.county,
        )
        self.url = reverse("accounts:create_user")
        self.password = secrets.token_urlsafe(32)
        self.data = {
            "first_name": "Anne-Marie",
            "last_name": "O’Njeri Wanjiku",
            "email": "Anne@example.invalid",
            "role": User.Role.OFFICER,
            "password": self.password,
        }

    def test_county_admin_creates_staff_with_email_login_and_no_username_field(self):
        self.client.force_login(self.admin)
        page = self.client.get(self.url)
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'name="username"')
        self.assertNotContains(page, 'name="county"')
        self.assertNotContains(page, "Choose a stronger password")

        response = self.client.post(self.url, {**self.data, "county": self.other_county.pk})
        self.assertRedirects(response, reverse("dashboard:county"), fetch_redirect_response=False)
        user = User.objects.get(email="anne@example.invalid")
        self.assertEqual(user.username, user.email)
        self.assertEqual(user.first_name, "Anne-Marie")
        self.assertEqual(user.last_name, "O’Njeri Wanjiku")
        self.assertEqual(user.county, self.county)
        self.assertTrue(user.check_password(self.password))
        self.client.logout()
        login = self.client.post(reverse("accounts:login"), {
            "username": "ANNE@EXAMPLE.INVALID", "password": self.password,
        })
        self.assertRedirects(login, reverse("dashboard:home"), fetch_redirect_response=False)

    def test_county_admin_cannot_grant_administrator_role(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {**self.data, "role": User.Role.SYSTEM_ADMIN})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="anne@example.invalid").exists())
        self.assertIn("role", response.context["form"].errors)

    def test_weak_password_errors_appear_only_after_submission(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {**self.data, "password": "password"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a stronger password")
        self.assertIn("password", response.context["form"].errors)
        self.assertFalse(User.objects.filter(email="anne@example.invalid").exists())

    def test_email_must_be_unique_ignoring_case(self):
        User.objects.create_user("legacy", email="anne@example.invalid", password=self.password)
        self.client.force_login(self.admin)
        response = self.client.post(self.url, self.data)
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.filter(email__iexact="anne@example.invalid").count(), 1)

    def test_system_admin_must_assign_county_for_county_staff(self):
        system_admin = User.objects.create_superuser("root", "root@example.invalid", self.password)
        self.client.force_login(system_admin)
        page = self.client.get(self.url)
        self.assertContains(page, 'name="county"')
        missing = self.client.post(self.url, self.data)
        self.assertIn("county", missing.context["form"].errors)
        valid = self.client.post(self.url, {**self.data, "county": self.other_county.pk})
        self.assertRedirects(valid, reverse("dashboard:county"), fetch_redirect_response=False)
        self.assertEqual(User.objects.get(email="anne@example.invalid").county, self.other_county)

    def test_non_admin_cannot_add_staff(self):
        officer = User.objects.create_user("officer", password=self.password, role=User.Role.OFFICER)
        self.client.force_login(officer)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)

    def test_email_login_follows_staff_profile_email_change(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, self.data)
        staff = User.objects.get(email="anne@example.invalid")
        self.client.force_login(staff)
        response = self.client.post(reverse("accounts:profile"), {
            "first_name": staff.first_name,
            "last_name": staff.last_name,
            "email": "New.Address@example.invalid",
            "phone": "",
            "job_title": "",
        })
        self.assertRedirects(response, reverse("accounts:profile"), fetch_redirect_response=False)
        staff.refresh_from_db()
        self.assertEqual(staff.username, "new.address@example.invalid")
        self.client.logout()
        self.assertTrue(self.client.login(username=staff.email, password=self.password))
