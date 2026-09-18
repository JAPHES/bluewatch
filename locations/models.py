from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

LAT_VALIDATORS = [MinValueValidator(-90), MaxValueValidator(90)]
LNG_VALIDATORS = [MinValueValidator(-180), MaxValueValidator(180)]

class County(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    is_coastal = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    class Meta: ordering = ["name"]; verbose_name_plural = "counties"
    def __str__(self): return self.name

class Ward(models.Model):
    county = models.ForeignKey(County, on_delete=models.PROTECT, related_name="wards")
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    class Meta: ordering = ["county__name", "name"]; constraints = [models.UniqueConstraint(fields=["county", "name"], name="unique_county_ward")]
    def __str__(self): return f"{self.name}, {self.county}"

class AuthorizedSite(models.Model):
    class Status(models.TextChoices):
        OPERATING = "operating", "Operating"
        LIMITED = "limited", "Limited"
        CLOSED = "closed", "Closed"
    name = models.CharField(max_length=160)
    county = models.ForeignKey(County, on_delete=models.PROTECT, related_name="authorized_sites")
    ward = models.ForeignKey(Ward, on_delete=models.PROTECT, related_name="authorized_sites")
    site_type = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, validators=LAT_VALIDATORS)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, validators=LNG_VALIDATORS)
    operating_status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPERATING)
    description = models.TextField(blank=True)
    managing_organization = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class SensitiveLocation(models.Model):
    class Type(models.TextChoices):
        RIVER="river","River"; DRAIN="drain","Drainage channel"; BEACH="beach","Beach"
        MANGROVE="mangrove","Mangrove"; WETLAND="wetland","Wetland"; MPA="mpa","Marine protected area"
        SCHOOL="school","School"; MARKET="market","Market"; RESIDENTIAL="residential","Residential area"
    name = models.CharField(max_length=160)
    location_type = models.CharField(max_length=20, choices=Type.choices)
    county = models.ForeignKey(County, null=True, blank=True, on_delete=models.SET_NULL, related_name="sensitive_locations")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, validators=LAT_VALIDATORS)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, validators=LNG_VALIDATORS)
    protection_radius_m = models.PositiveIntegerField(default=500)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class PlatformSetting(models.Model):
    key = models.SlugField(unique=True)
    value = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.key
