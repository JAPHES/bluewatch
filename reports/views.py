from django.contrib import messages
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from accounts.access import roles_required
from bluewatch.config import RATE_LIMIT_REPORTS, RATE_LIMIT_WINDOW_SECONDS
from notifications.services import notify_critical_report
from locations.models import County, Ward
from locations.services import LocationResolutionError, resolve_report_location
from .forms import OfficerReportForm, PublicReportForm, TrackingForm
from .models import Report, ReportActivity, WasteCategory
from .services import assess_authorized_site, calculate_risk, find_duplicate, transition_report

def _rate_key(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    return "report-rate:" + (forwarded or request.META.get("REMOTE_ADDR", "unknown"))


@require_GET
def resolve_location(request):
    rate_key = f"location-lookup:{_rate_key(request)}"
    lookup_count = cache.get(rate_key, 0)
    if lookup_count >= 30:
        return JsonResponse({"ok": False, "error": "Too many location checks. Please try again later."}, status=429)
    try:
        latitude = float(request.GET.get("latitude", "")); longitude = float(request.GET.get("longitude", ""))
        resolved = resolve_report_location(latitude, longitude)
    except (TypeError, ValueError, LocationResolutionError) as exc:
        return JsonResponse({"ok": False, "error": str(exc) or "Select a valid map point."}, status=422)
    cache.set(rate_key, lookup_count + 1, 60 * 60)
    payload = {"latitude": round(latitude, 6), "longitude": round(longitude, 6), "county_id": resolved["county"].pk, "ward_id": resolved["ward"].pk, "location_description": resolved["location_description"], "proximity_to_water": resolved["proximity_to_water"], "water_label": resolved["water_label"]}
    token = signing.dumps(payload, salt="public-report-location", compress=True)
    return JsonResponse({"ok": True, "county": resolved["county"].name, "ward": resolved["ward"].name, "location": resolved["location_description"], "water": resolved["water_label"], "token": token})

@require_http_methods(["GET", "POST"])
def submit_report(request):
    form = PublicReportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        key = _rate_key(request); count = cache.get(key, 0)
        if count >= RATE_LIMIT_REPORTS:
            form.add_error(None, "Too many recent submissions. Please try again later.")
        else:
            try:
                location = signing.loads(form.cleaned_data["location_token"], salt="public-report-location", max_age=60 * 60)
                if abs(float(form.cleaned_data["latitude"]) - float(location["latitude"])) > 0.000002 or abs(float(form.cleaned_data["longitude"]) - float(location["longitude"])) > 0.000002:
                    raise signing.BadSignature
                county = County.objects.get(pk=location["county_id"], is_active=True)
                ward = Ward.objects.get(pk=location["ward_id"], county=county, is_active=True)
                category = WasteCategory.objects.get(slug="unclassified", is_active=True)
            except (signing.BadSignature, signing.SignatureExpired, County.DoesNotExist, Ward.DoesNotExist, WasteCategory.DoesNotExist, KeyError):
                form.add_error(None, "Detect the location again before submitting this report.")
                return render(request, "reports/submit.html", {"form": form})
            report = Report.objects.create(source=Report.Source.PUBLIC, county=county, ward=ward,
                location_description=location["location_description"], latitude=location["latitude"], longitude=location["longitude"],
                original_image=form.cleaned_data["original_image"], waste_category=category, estimated_size=Report.Size.UNKNOWN,
                proximity_to_water=location["proximity_to_water"], description="Quick public photo report; classification and details require officer review.",
                date_observed=timezone.localdate(), reporter_email=form.cleaned_data["reporter_email"])
            assess_authorized_site(report)
            duplicate = find_duplicate(report)
            if duplicate: report.possible_duplicate_of = duplicate
            report.risk_score, report.risk_level = calculate_risk(report)
            report.save(update_fields=["near_authorized_site", "authorized_site_note", "possible_duplicate_of", "risk_score", "risk_level", "updated_at"])
            ReportActivity.objects.create(report=report, action="Public report submitted", new_value=report.operational_status)
            cache.set(key, count + 1, RATE_LIMIT_WINDOW_SECONDS)
            if report.risk_level == Report.Risk.CRITICAL: notify_critical_report(report)
            request.session["submitted_reference"] = report.reference_code
            return redirect("reports:confirmation")
    return render(request, "reports/submit.html", {"form": form})

def confirmation(request):
    code = request.session.pop("submitted_reference", None)
    if not code: return redirect("reports:submit")
    return render(request, "reports/confirmation.html", {"reference_code": code})

@require_http_methods(["GET", "POST"])
def track(request):
    form = TrackingForm(request.POST or None); report = None
    if request.method == "POST" and form.is_valid():
        report = Report.objects.filter(reference_code=form.cleaned_data["reference_code"], is_archived=False).first()
        if not report: form.add_error("reference_code", "No active report was found with that reference.")
    return render(request, "reports/track.html", {"form": form, "report": report})

@roles_required("system_admin", "county_admin", "officer", "analyst")
def report_detail(request, reference_code):
    report = get_object_or_404(Report, reference_code=reference_code)
    if request.user.county_id and report.county_id != request.user.county_id and not request.user.is_superuser: raise PermissionDenied
    form = OfficerReportForm(instance=report)
    return render(request, "reports/detail.html", {"report":report, "form":form})

@roles_required("system_admin", "county_admin", "officer")
@require_http_methods(["POST"])
def update_report(request, reference_code):
    report = get_object_or_404(Report, reference_code=reference_code)
    if request.user.county_id and report.county_id != request.user.county_id and not request.user.is_superuser: raise PermissionDenied
    old_verification, old_status, old_officer_id = report.verification_status, report.operational_status, report.assigned_officer_id
    form = OfficerReportForm(request.POST, instance=report)
    if form.is_valid():
        desired_status = form.cleaned_data["operational_status"]
        report.operational_status = old_status
        report.save()
        if old_verification != report.verification_status:
            ReportActivity.objects.create(report=report, action="Verification changed", previous_value=old_verification, new_value=report.verification_status, responsible_user=request.user, note=form.cleaned_data["note"])
        if desired_status != old_status:
            try: transition_report(report, desired_status, request.user, form.cleaned_data["note"])
            except ValueError as exc: messages.error(request, str(exc)); return redirect("reports:detail", reference_code=reference_code)
        if report.assigned_officer_id and report.assigned_officer_id != old_officer_id:
            from notifications.services import create_notification
            create_notification(report.assigned_officer, "Report assigned to you", f"You are responsible for reviewing {report.reference_code}.", f"/reports/case/{report.reference_code}/", "report-assigned")
        messages.success(request, "Report updated.")
    else: messages.error(request, "Please correct the update form.")
    return redirect("reports:detail", reference_code=reference_code)
