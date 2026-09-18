import secrets
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from bluewatch.config import MAX_IMAGE_BYTES

def validate_image(upload):
    if upload.size > MAX_IMAGE_BYTES: raise ValidationError("Image must be 5 MB or smaller.")
    try:
        image = Image.open(upload); image.verify(); upload.seek(0)
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("Upload a valid JPEG, PNG, or WebP image.")
    if image.format not in {"JPEG", "PNG", "WEBP"}: raise ValidationError("Only JPEG, PNG, and WebP images are accepted.")

def safe_report_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f"uploads/reports/{timezone.now():%Y/%m}/{secrets.token_hex(16)}{suffix}"

def generate_reference():
    while True:
        code = f"BW-{timezone.now():%y%m}-{secrets.token_hex(3).upper()}"
        if not Report.objects.filter(reference_code=code).exists(): return code

class WasteCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(unique=True)
    risk_weight = models.PositiveSmallIntegerField(default=5)
    hazardous = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Report(models.Model):
    class Source(models.TextChoices): PUBLIC="public","Public"; OFFICER="officer","Officer"
    class Size(models.TextChoices): SMALL="small","Small (a few bags)"; MEDIUM="medium","Medium (pickup load)"; LARGE="large","Large (truck load)"; EXTENSIVE="extensive","Extensive"
    class Water(models.TextChoices): IN_WATER="in_water","In water"; UNDER_50="under_50","Under 50 metres"; UNDER_200="under_200","50–200 metres"; OVER_200="over_200","Over 200 metres"; UNKNOWN="unknown","Unknown"
    class Verification(models.TextChoices): PENDING="pending","Pending"; VERIFIED="verified","Verified"; REJECTED="rejected","Rejected"; DUPLICATE="duplicate","Duplicate"; NEEDS_INFO="needs_info","Needs More Information"
    class Status(models.TextChoices): REPORTED="reported","Reported"; REVIEW="under_review","Under Review"; VERIFIED="verified","Verified"; ASSIGNED="assigned","Assigned"; IN_PROGRESS="cleanup_in_progress","Cleanup in Progress"; CLEANED="cleaned","Cleaned"; CLOSED="closed","Closed"
    class Risk(models.TextChoices): LOW="low","Low"; MODERATE="moderate","Moderate"; HIGH="high","High"; CRITICAL="critical","Critical"
    class Analysis(models.TextChoices): NOT_ANALYSED="not_analysed","Not Analysed"; PENDING="pending","Pending"; COMPLETED="completed","Completed"; FAILED="failed","Failed"; HUMAN_REVIEW="human_review","Requires Human Review"
    reference_code = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.PUBLIC)
    reporter_name = models.CharField(max_length=120, blank=True)
    reporter_phone = models.CharField(max_length=30, blank=True)
    reporter_email = models.EmailField(blank=True)
    county = models.ForeignKey("locations.County", on_delete=models.PROTECT, related_name="reports")
    ward = models.ForeignKey("locations.Ward", on_delete=models.PROTECT, related_name="reports")
    location_description = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    original_image = models.ImageField(upload_to=safe_report_path, validators=[validate_image])
    waste_category = models.ForeignKey(WasteCategory, on_delete=models.PROTECT, related_name="reports")
    estimated_size = models.CharField(max_length=20, choices=Size.choices)
    proximity_to_water = models.CharField(max_length=20, choices=Water.choices)
    description = models.TextField()
    date_observed = models.DateField()
    date_submitted = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(max_length=20, choices=Verification.choices, default=Verification.PENDING)
    operational_status = models.CharField(max_length=30, choices=Status.choices, default=Status.REPORTED)
    risk_score = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=12, choices=Risk.choices, default=Risk.LOW)
    assigned_officer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_reports")
    possible_duplicate_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="possible_duplicates")
    near_authorized_site = models.BooleanField(default=False)
    authorized_site_note = models.CharField(max_length=255, blank=True)
    analysis_status = models.CharField(max_length=20, choices=Analysis.choices, default=Analysis.NOT_ANALYSED)
    analysis_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    suggested_category = models.ForeignKey(WasteCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="analysis_suggestions")
    analysis_notes = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["-date_submitted"]
    def save(self, *args, **kwargs):
        if not self.reference_code: self.reference_code = generate_reference()
        super().save(*args, **kwargs)
    def __str__(self): return self.reference_code

class ReportActivity(models.Model):
    report = models.ForeignKey(Report, on_delete=models.PROTECT, related_name="activities")
    action = models.CharField(max_length=100)
    previous_value = models.CharField(max_length=100, blank=True)
    new_value = models.CharField(max_length=100, blank=True)
    responsible_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-timestamp"]

class MarineImpactRecord(models.Model):
    report = models.OneToOneField(Report, on_delete=models.PROTECT, related_name="impact_record")
    waste_removed_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recycled_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    high_risk_near_water_resolved = models.BooleanField(default=False)
    recorded_at = models.DateTimeField(auto_now_add=True)
