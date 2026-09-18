import base64
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from locations.models import County,Ward
from reports.models import MarineImpactRecord,Report,WasteCategory
from .models import CleanupAssignment,CleanupTeam

PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
def image(name): return SimpleUploadedFile(name,PNG,content_type="image/png")

class CleanupTests(TestCase):
    def setUp(self):
        self.c1=County.objects.create(name="Coast One",code="C1"); self.w1=Ward.objects.create(county=self.c1,name="Bay")
        self.c2=County.objects.create(name="Coast Two",code="C2"); self.w2=Ward.objects.create(county=self.c2,name="Creek")
        self.category=WasteCategory.objects.create(name="Mixed",slug="mixed")
        self.officer=User.objects.create_user("officer",password="StrongPass!789",role="officer",county=self.c1)
        self.other=User.objects.create_user("other",password="StrongPass!789",role="officer",county=self.c2)
        self.member=User.objects.create_user("member",password="StrongPass!789",role="team_member",county=self.c1)
        self.team=CleanupTeam.objects.create(name="Bay crew",county=self.c1); self.team.members.add(self.member)
        self.report=Report.objects.create(county=self.c1,ward=self.w1,location_description="Demo bay",latitude=-4.1,longitude=39.6,original_image=image("report.png"),waste_category=self.category,estimated_size="large",proximity_to_water="under_50",description="Test report",date_observed=timezone.localdate(),verification_status="verified",operational_status="assigned",assigned_officer=self.officer)
        self.assignment=CleanupAssignment.objects.create(report=self.report,assigned_team=self.team,assigned_officer=self.officer,priority="high",scheduled_cleanup_date=timezone.localdate()+timedelta(days=1),instructions="Collect safely")
    def test_cleanup_assignment_exists_and_team_member_can_access(self):
        self.client.force_login(self.member); self.assertEqual(self.client.get(reverse("operations:detail",args=[self.assignment.pk])).status_code,200)
    def test_other_county_cannot_access_assignment(self):
        self.client.force_login(self.other); self.assertEqual(self.client.get(reverse("operations:detail",args=[self.assignment.pk])).status_code,403)
    def test_cleanup_verification_closes_evidence_loop(self):
        self.assignment.assignment_status="submitted"; self.assignment.after_photo=image("after.png"); self.assignment.estimated_waste_collected_kg=125; self.assignment.disposal_destination="Licensed demo facility"; self.assignment.completion_notes="Area cleared"; self.assignment.save()
        self.report.operational_status="cleanup_in_progress"; self.report.save()
        self.client.force_login(self.officer); response=self.client.post(reverse("operations:verify",args=[self.assignment.pk])); self.assertRedirects(response,reverse("operations:detail",args=[self.assignment.pk]))
        self.assignment.refresh_from_db(); self.report.refresh_from_db(); self.assertEqual(self.assignment.assignment_status,"completed"); self.assertEqual(self.assignment.verified_by,self.officer); self.assertEqual(self.report.operational_status,"cleaned"); self.assertTrue(MarineImpactRecord.objects.filter(report=self.report).exists())

