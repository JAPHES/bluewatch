import secrets

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from locations.models import County, Ward
from reports.models import Report, WasteCategory


class PublicDashboardTests(TestCase):
    def test_public_impact_dashboard_is_public(self):
        response = self.client.get(reverse("dashboard:public"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "site-footer")
    def test_public_dashboard_uses_configured_map_provider(self):
        response=self.client.get(reverse("dashboard:public"))
        self.assertContains(response,"services.arcgisonline.com/ArcGIS/rest/services/World_Street_Map")
        self.assertContains(response,"tiles.openfreemap.org/styles/liberty")
        self.assertContains(response,"satelliteMaxNativeZoom:18")
        self.assertNotContains(response,"tile.openstreetmap.org")


class CountyDashboardLayoutTests(TestCase):
    def setUp(self):
        county = County.objects.create(name="Demo Coast", code="DC")
        other_county = County.objects.create(name="Other Coast", code="OC")
        ward = Ward.objects.create(county=county, name="Harbour")
        other_ward = Ward.objects.create(county=other_county, name="Beach")
        category = WasteCategory.objects.create(name="Plastic", slug="plastic")
        self.officer = User.objects.create_user(
            "dashboard.officer", password=secrets.token_urlsafe(32), role="officer", county=county,
        )
        self.team_member = User.objects.create_user(
            "dashboard.team", password=secrets.token_urlsafe(32), role="team_member", county=county,
        )
        details = {
            "location_description": "Near the demo bridge",
            "latitude": -4.04,
            "longitude": 39.67,
            "original_image": "uploads/reports/demo.png",
            "waste_category": category,
            "estimated_size": "medium",
            "proximity_to_water": "unknown",
            "description": "Test report",
            "date_observed": timezone.localdate(),
        }
        self.report = Report.objects.create(county=county, ward=ward, **details)
        self.other_report = Report.objects.create(county=other_county, ward=other_ward, **details)

    def test_county_dashboard_is_map_only_and_county_scoped(self):
        self.client.force_login(self.officer)
        response = self.client.get(reverse("dashboard:county"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="ops-map"')
        self.assertContains(response, 'id="county-map-page"')
        self.assertContains(response, 'fitMapToScreen()')
        self.assertContains(response, '<summary>Filter reports</summary>')
        self.assertNotContains(response, 'site-footer')
        self.assertContains(response, self.report.reference_code)
        self.assertNotContains(response, self.other_report.reference_code)
        self.assertContains(response, reverse("dashboard:county_insights"))
        for moved_section in ("Risk distribution", "Reports over time", "Waste categories", "Recent reports", "Overdue assignments", "Recurring hotspots", 'id="riskChart"'):
            self.assertNotContains(response, moved_section)

    def test_insights_preserves_sections_filters_and_county_scope(self):
        self.client.force_login(self.officer)
        response = self.client.get(reverse("dashboard:county_insights"), {"risk": "low"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.report.reference_code)
        self.assertNotContains(response, self.other_report.reference_code)
        self.assertContains(response, 'value="low" selected')
        self.assertContains(response, 'href="/dashboard/county/?risk=low"')
        for moved_section in ("Risk distribution", "Reports over time", "Waste categories", "Recent reports", "Overdue assignments", "Recurring hotspots"):
            self.assertContains(response, moved_section)
        self.assertNotContains(response, 'id="ops-map"')

    def test_dashboard_and_insights_require_authorised_staff(self):
        for name in ("dashboard:county", "dashboard:county_insights"):
            url = reverse(name)
            self.assertRedirects(self.client.get(url), reverse("accounts:login") + "?next=" + url, fetch_redirect_response=False)
            self.client.force_login(self.team_member)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.client.logout()
