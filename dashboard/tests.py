from django.test import TestCase
from django.urls import reverse
class PublicDashboardTests(TestCase):
    def test_public_impact_dashboard_is_public(self): self.assertEqual(self.client.get(reverse("dashboard:public")).status_code,200)
