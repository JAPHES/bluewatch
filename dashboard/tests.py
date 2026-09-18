from django.test import TestCase
from django.urls import reverse
class PublicDashboardTests(TestCase):
    def test_public_impact_dashboard_is_public(self): self.assertEqual(self.client.get(reverse("dashboard:public")).status_code,200)
    def test_public_dashboard_uses_configured_map_provider(self):
        response=self.client.get(reverse("dashboard:public"))
        self.assertContains(response,"services.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map")
        self.assertNotContains(response,"tile.openstreetmap.org")
