from django.test import TestCase
from django.urls import reverse
class HealthTests(TestCase):
    def test_health_check(self):
        response=self.client.get(reverse("core:health")); self.assertEqual(response.status_code,200); self.assertEqual(response.json()["status"],"ok")
    def test_public_content_pages_render(self):
        for name in ["core:home","core:about","core:how","core:contact"]:
            with self.subTest(name=name): self.assertEqual(self.client.get(reverse(name)).status_code,200)
