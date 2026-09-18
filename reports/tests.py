import base64
import secrets
from datetime import timedelta
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from locations.models import County,SensitiveLocation,Ward
from .models import Report,WasteCategory
from .services import calculate_risk,find_duplicate,transition_report

PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
def upload(name="evidence.png",content=PNG): return SimpleUploadedFile(name,content,content_type="image/png")

class ReportTestBase(TestCase):
    def setUp(self):
        cache.clear(); self.county=County.objects.create(name="Test Coast",code="TC")
        self.ward=Ward.objects.create(county=self.county,name="Harbour")
        self.category=WasteCategory.objects.create(name="Plastic",slug="plastic",risk_weight=8)
    def make_report(self,**overrides):
        data={"county":self.county,"ward":self.ward,"location_description":"Near the demo bridge","latitude":-4.040000,"longitude":39.670000,"original_image":upload(),"waste_category":self.category,"estimated_size":"medium","proximity_to_water":"under_50","description":"Discarded waste visible from a safe public path.","date_observed":timezone.localdate()}
        data.update(overrides); return Report.objects.create(**data)

class AnonymousReportingTests(ReportTestBase):
    def payload(self): return {"county":self.county.pk,"ward":self.ward.pk,"location_description":"Near the demo bridge","latitude":"-4.040000","longitude":"39.670000","waste_category":self.category.pk,"estimated_size":"medium","proximity_to_water":"under_50","description":"Discarded waste visible from a safe public path.","date_observed":timezone.localdate().isoformat(),"reporter_name":"Private Person","reporter_phone":"+254700111222","reporter_email":"private@example.invalid","consent":"on","truthful":"on","original_image":upload()}
    def test_anonymous_submission_and_reference(self):
        response=self.client.post(reverse("reports:submit"),self.payload())
        self.assertRedirects(response,reverse("reports:confirmation")); report=Report.objects.get()
        self.assertRegex(report.reference_code,r"^BW-\d{4}-[A-F0-9]{6}$")
    def test_honeypot_rejects_submission(self):
        data=self.payload(); data["website"]="spam.example"
        self.assertEqual(self.client.post(reverse("reports:submit"),data).status_code,200); self.assertFalse(Report.objects.exists())
    def test_invalid_file_content_is_rejected(self):
        data=self.payload(); data["original_image"]=upload("fake.png",b"not an image")
        response=self.client.post(reverse("reports:submit"),data); self.assertContains(response,"valid image"); self.assertFalse(Report.objects.exists())
    def test_tracking_excludes_private_reporter_data(self):
        report=self.make_report(reporter_name="Secret Name",reporter_phone="0700111222",reporter_email="secret@example.invalid")
        response=self.client.post(reverse("reports:track"),{"reference_code":report.reference_code})
        self.assertContains(response,report.reference_code); self.assertNotContains(response,"Secret Name"); self.assertNotContains(response,"0700111222"); self.assertNotContains(response,"secret@example.invalid")

class ServiceTests(ReportTestBase):
    def test_risk_scoring_is_rule_based_and_sensitive_to_water(self):
        SensitiveLocation.objects.create(name="Demo creek",location_type="river",county=self.county,latitude=-4.04,longitude=39.67,protection_radius_m=1000)
        report=self.make_report(estimated_size="extensive",proximity_to_water="in_water")
        score,level=calculate_risk(report); self.assertGreaterEqual(score,70); self.assertEqual(level,"critical")
    def test_duplicate_detection_by_distance_time_and_category(self):
        primary=self.make_report(); candidate=self.make_report(latitude=-4.0401,longitude=39.6701)
        self.assertEqual(find_duplicate(candidate),primary)
    def test_valid_and_invalid_status_transitions(self):
        user=User.objects.create_user("officer",password=secrets.token_urlsafe(32),role="officer",county=self.county)
        report=self.make_report(verification_status="verified",operational_status="under_review")
        transition_report(report,"verified",user,"Checked evidence"); report.refresh_from_db(); self.assertEqual(report.operational_status,"verified"); self.assertEqual(report.activities.count(),1)
        with self.assertRaises(ValueError): transition_report(report,"closed",user)
    def test_unverified_cannot_be_cleaned(self):
        user=User.objects.create_user("officer2",password=secrets.token_urlsafe(32),role="officer",county=self.county); report=self.make_report()
        with self.assertRaises(ValueError): transition_report(report,"cleaned",user)
