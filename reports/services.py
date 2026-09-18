from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from bluewatch import config
from locations.models import AuthorizedSite, SensitiveLocation
from locations.services import distance_km
from .models import Report, ReportActivity

WATER_TYPES = {"river", "drain", "beach", "wetland", "mangrove", "mpa"}
PEOPLE_TYPES = {"school", "market", "residential"}

def nearby(items, report, maximum_km):
    return [x for x in items if distance_km(report.latitude, report.longitude, x.latitude, x.longitude) <= float(maximum_km)]

def assess_authorized_site(report):
    matches = nearby(AuthorizedSite.objects.filter(is_active=True, county=report.county), report, config.AUTHORIZED_SITE_REVIEW_RADIUS_KM)
    report.near_authorized_site = bool(matches)
    report.authorized_site_note = f"Near registered site: {matches[0].name}" if matches else ""

def find_duplicate(report):
    since = timezone.now() - timedelta(days=config.DUPLICATE_WINDOW_DAYS)
    candidates = Report.objects.filter(date_submitted__gte=since, waste_category=report.waste_category, is_archived=False).exclude(pk=report.pk).exclude(operational_status=Report.Status.CLOSED)
    return next(iter(nearby(candidates, report, config.DUPLICATE_DISTANCE_KM)), None)

def calculate_risk(report):
    score = report.waste_category.risk_weight
    score += {Report.Size.SMALL: 2, Report.Size.MEDIUM: 8, Report.Size.LARGE: 15, Report.Size.EXTENSIVE: 25}[report.estimated_size]
    score += {Report.Water.IN_WATER: 35, Report.Water.UNDER_50: 25, Report.Water.UNDER_200: 12, Report.Water.OVER_200: 2, Report.Water.UNKNOWN: 5}[report.proximity_to_water]
    sensitive = SensitiveLocation.objects.filter(is_active=True).filter(Q(county=report.county) | Q(county__isnull=True))
    for place in sensitive:
        if distance_km(report.latitude, report.longitude, place.latitude, place.longitude) <= place.protection_radius_m / 1000:
            score += 18 if place.location_type in WATER_TYPES else 10
    close_reports = nearby(Report.objects.filter(county=report.county, is_archived=False).exclude(pk=report.pk), report, config.NEARBY_REPORT_DISTANCE_KM)
    score += min(len(close_reports) * 4, 16)
    if report.pk and report.operational_status != Report.Status.CLOSED:
        score += min((timezone.now().date() - report.date_submitted.date()).days // 7 * 3, 15)
    score = min(score, 100)
    if score >= config.RISK_THRESHOLDS["critical"]: level = Report.Risk.CRITICAL
    elif score >= config.RISK_THRESHOLDS["high"]: level = Report.Risk.HIGH
    elif score >= config.RISK_THRESHOLDS["moderate"]: level = Report.Risk.MODERATE
    else: level = Report.Risk.LOW
    return score, level

ALLOWED_TRANSITIONS = {
    Report.Status.REPORTED: {Report.Status.REVIEW}, Report.Status.REVIEW: {Report.Status.VERIFIED, Report.Status.REPORTED},
    Report.Status.VERIFIED: {Report.Status.ASSIGNED}, Report.Status.ASSIGNED: {Report.Status.IN_PROGRESS},
    Report.Status.IN_PROGRESS: {Report.Status.CLEANED}, Report.Status.CLEANED: {Report.Status.CLOSED, Report.Status.IN_PROGRESS},
    Report.Status.CLOSED: set(),
}

def transition_report(report, new_status, user, note="", override=False):
    old = report.operational_status
    if new_status not in ALLOWED_TRANSITIONS.get(old, set()) and not override:
        raise ValueError(f"Invalid transition from {report.get_operational_status_display()} to {dict(Report.Status.choices).get(new_status, new_status)}.")
    if new_status in {Report.Status.VERIFIED, Report.Status.ASSIGNED, Report.Status.IN_PROGRESS, Report.Status.CLEANED, Report.Status.CLOSED} and report.verification_status != Report.Verification.VERIFIED and not override:
        raise ValueError("The report must be verified before this status can be applied.")
    if override and not note.strip(): raise ValueError("An override explanation is required.")
    report.operational_status = new_status; report.save(update_fields=["operational_status", "updated_at"])
    ReportActivity.objects.create(report=report, action="Operational status changed", previous_value=old, new_value=new_status, responsible_user=user, note=note)
    if new_status == Report.Status.CLOSED and report.assigned_officer:
        from notifications.services import create_notification
        create_notification(report.assigned_officer, "Case closed", f"{report.reference_code} has been closed.", f"/reports/case/{report.reference_code}/", "case-closed")

class ReportAnalysisService:
    """Interface for a future image or earth-observation analysis provider."""
    def analyse(self, report):
        raise NotImplementedError("No automated analysis provider is configured.")
