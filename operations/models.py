import secrets
from pathlib import Path
from django.conf import settings
from django.db import models
from django.utils import timezone
from reports.models import validate_image

def evidence_path(instance, filename):
    return f"uploads/evidence/{timezone.now():%Y/%m}/{secrets.token_hex(16)}{Path(filename).suffix.lower()}"

class CleanupTeam(models.Model):
    name = models.CharField(max_length=140)
    county = models.ForeignKey("locations.County", on_delete=models.PROTECT, related_name="cleanup_teams")
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="cleanup_teams")
    contact_phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class CleanupAssignment(models.Model):
    class Priority(models.TextChoices): ROUTINE="routine","Routine"; HIGH="high","High"; URGENT="urgent","Urgent"
    class Status(models.TextChoices): NEW="new","New"; SCHEDULED="scheduled","Scheduled"; IN_PROGRESS="in_progress","In Progress"; SUBMITTED="submitted","Submitted for Verification"; COMPLETED="completed","Completed"; CANCELLED="cancelled","Cancelled"
    report = models.ForeignKey("reports.Report", on_delete=models.PROTECT, related_name="assignments")
    assigned_team = models.ForeignKey(CleanupTeam, on_delete=models.PROTECT, related_name="assignments")
    assigned_officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_assignments")
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.ROUTINE)
    scheduled_cleanup_date = models.DateField()
    instructions = models.TextField()
    assignment_status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    start_time = models.DateTimeField(null=True, blank=True)
    completion_time = models.DateTimeField(null=True, blank=True)
    estimated_waste_collected_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    disposal_destination = models.CharField(max_length=200, blank=True)
    waste_diverted_for_recycling_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    before_photo = models.ImageField(upload_to=evidence_path, validators=[validate_image], blank=True)
    after_photo = models.ImageField(upload_to=evidence_path, validators=[validate_image], blank=True)
    completion_notes = models.TextField(blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="verified_assignments")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["scheduled_cleanup_date"]
    def __str__(self): return f"{self.report.reference_code} — {self.assigned_team}"

