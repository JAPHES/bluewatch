from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def validate_polygon(value):
    if not isinstance(value, dict) or value.get("type") != "Polygon":
        raise ValidationError("The selected area must be a GeoJSON Polygon.")
    rings = value.get("coordinates")
    if not rings or not isinstance(rings[0], list) or len(rings[0]) < 4:
        raise ValidationError("Draw a polygon with at least three points.")
    if len(rings[0]) > 500:
        raise ValidationError("The area boundary cannot contain more than 500 points.")
    for point in rings[0]:
        if not isinstance(point, list) or len(point) < 2:
            raise ValidationError("The area contains an invalid coordinate.")
        try:
            lng, lat = map(float, point[:2])
        except (TypeError, ValueError):
            raise ValidationError("The area contains a non-numeric coordinate.")
        if not (-180 <= lng <= 180 and -90 <= lat <= 90):
            raise ValidationError("The area contains a coordinate outside valid bounds.")


class AreaOfInterest(models.Model):
    name = models.CharField(max_length=160)
    county = models.ForeignKey("locations.County", on_delete=models.PROTECT, related_name="observation_areas")
    ward = models.ForeignKey("locations.Ward", null=True, blank=True, on_delete=models.PROTECT, related_name="observation_areas")
    boundary = models.JSONField(validators=[validate_polygon])
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_observation_areas")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["county", "name"], name="unique_county_observation_area")]

    def clean(self):
        super().clean()
        validate_polygon(self.boundary)
        if self.ward_id and self.ward.county_id != self.county_id:
            raise ValidationError({"ward": "The ward must belong to the selected county."})

    def __str__(self):
        return f"{self.name} — {self.county}"


class ObservationSurvey(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready for Review"
        IN_REVIEW = "in_review", "In Review"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Method(models.TextChoices):
        VISUAL = "visual", "Human visual review"
        EXTERNAL = "external", "External analysis provider"

    area = models.ForeignKey(AreaOfInterest, on_delete=models.PROTECT, related_name="surveys")
    title = models.CharField(max_length=180)
    imagery_source = models.CharField(max_length=160, default="Configured satellite imagery basemap")
    imagery_capture_date = models.DateField(null=True, blank=True)
    imagery_reference = models.URLField(blank=True, help_text="Optional source, catalogue, or scene URL.")
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.VISUAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    provider_job_id = models.CharField(max_length=160, blank=True)
    provider_notes = models.TextField(blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="observation_surveys")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_observation_surveys")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ObservationCandidate(models.Model):
    class ReviewStatus(models.TextChoices):
        UNREVIEWED = "unreviewed", "Unreviewed"
        SUSPECTED = "suspected", "Suspected Dumpsite"
        DISMISSED = "dismissed", "Dismissed"
        REPORT_CREATED = "report_created", "Report Created"

    class DetectionSource(models.TextChoices):
        HUMAN = "human", "Human mapped"
        PROVIDER = "provider", "External provider suggestion"

    survey = models.ForeignKey(ObservationSurvey, on_delete=models.PROTECT, related_name="candidates")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=9, decimal_places=6, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    detection_source = models.CharField(max_length=20, choices=DetectionSource.choices, default=DetectionSource.HUMAN)
    provider_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    suggested_category = models.ForeignKey("reports.WasteCategory", null=True, blank=True, on_delete=models.SET_NULL, related_name="observation_candidates")
    description = models.TextField(blank=True)
    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.UNREVIEWED)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_observation_candidates")
    review_note = models.TextField(blank=True)
    linked_report = models.OneToOneField("reports.Report", null=True, blank=True, on_delete=models.PROTECT, related_name="observation_candidate")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Candidate {self.pk or 'new'} — {self.survey}"
