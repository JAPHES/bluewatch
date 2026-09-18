import base64
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from locations.models import County, Ward
from reports.models import Report, WasteCategory
from .models import AreaOfInterest, ObservationCandidate, ObservationSurvey
from .services import point_in_polygon

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
BOUNDARY = {"type": "Polygon", "coordinates": [[[39.60, -4.10], [39.75, -4.10], [39.75, -3.95], [39.60, -3.95], [39.60, -4.10]]]}


class EarthObservationTests(TestCase):
    def setUp(self):
        self.county = County.objects.create(name="Mapping Coast", code="MC")
        self.ward = Ward.objects.create(county=self.county, name="Ocean Ward")
        self.other_county = County.objects.create(name="Other Coast", code="OC")
        self.officer = User.objects.create_user("mapper", password="StrongPass!789", role="officer", county=self.county)
        self.other = User.objects.create_user("other_mapper", password="StrongPass!789", role="officer", county=self.other_county)
        self.team = User.objects.create_user("field_member", password="StrongPass!789", role="team_member", county=self.county)
        self.category = WasteCategory.objects.create(name="Mapped plastic", slug="mapped-plastic", risk_weight=8)
        self.area = AreaOfInterest.objects.create(name="Harbour scan", county=self.county, ward=self.ward, boundary=BOUNDARY, created_by=self.officer)
        self.survey = ObservationSurvey.objects.create(area=self.area, title="August imagery review", requested_by=self.officer, status="ready")

    def test_point_in_polygon(self):
        self.assertTrue(point_in_polygon(-4.04, 39.67, BOUNDARY))
        self.assertFalse(point_in_polygon(-4.40, 39.67, BOUNDARY))

    def test_authorised_user_can_open_workspace_and_survey(self):
        self.client.force_login(self.officer)
        self.assertEqual(self.client.get(reverse("earth_observation:workspace")).status_code, 200)
        self.assertEqual(self.client.get(reverse("earth_observation:create_area")).status_code, 200)
        self.assertEqual(self.client.get(reverse("earth_observation:area", args=[self.area.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("earth_observation:survey", args=[self.survey.pk])).status_code, 200)

    def test_team_member_cannot_open_mapping_workspace(self):
        self.client.force_login(self.team)
        self.assertEqual(self.client.get(reverse("earth_observation:workspace")).status_code, 403)

    def test_cross_county_survey_access_is_denied(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("earth_observation:survey", args=[self.survey.pk])).status_code, 403)

    def test_candidate_must_be_inside_area(self):
        self.client.force_login(self.officer)
        self.client.post(reverse("earth_observation:add_candidate", args=[self.survey.pk]), {"latitude": "-4.40", "longitude": "39.67", "suggested_category": self.category.pk, "description": "Outside"})
        self.assertFalse(ObservationCandidate.objects.exists())
        self.client.post(reverse("earth_observation:add_candidate", args=[self.survey.pk]), {"latitude": "-4.04", "longitude": "39.67", "suggested_category": self.category.pk, "description": "Visible waste-like accumulation"})
        candidate = ObservationCandidate.objects.get()
        self.assertEqual(candidate.detection_source, "human")

    def test_reviewed_candidate_converts_to_pending_report(self):
        candidate = ObservationCandidate.objects.create(survey=self.survey, latitude=-4.04, longitude=39.67, suggested_category=self.category, review_status="suspected", reviewed_by=self.officer, review_note="Distinct waste-like pile visible; field check required.")
        self.client.force_login(self.officer)
        response = self.client.post(reverse("earth_observation:convert_candidate", args=[candidate.pk]), {
            "ward": self.ward.pk, "waste_category": self.category.pk,
            "original_image": SimpleUploadedFile("licensed-extract.png", PNG, content_type="image/png"),
            "location_description": "Within Harbour scan area", "estimated_size": "medium",
            "proximity_to_water": "under_200", "description": "Mapped from licensed imagery; verify in field.",
            "date_observed": timezone.localdate().isoformat(),
        })
        self.assertEqual(response.status_code, 302)
        candidate.refresh_from_db(); report = Report.objects.get()
        self.assertEqual(candidate.linked_report, report)
        self.assertEqual(report.source, "officer")
        self.assertEqual(report.verification_status, "pending")
        self.assertEqual(report.operational_status, "under_review")
        self.assertEqual(report.analysis_status, "human_review")

    def test_unreviewed_candidate_cannot_convert(self):
        candidate = ObservationCandidate.objects.create(survey=self.survey, latitude=-4.04, longitude=39.67)
        self.client.force_login(self.officer)
        response = self.client.post(reverse("earth_observation:convert_candidate", args=[candidate.pk]), {})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Report.objects.exists())
