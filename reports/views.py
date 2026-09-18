from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from accounts.access import roles_required
from bluewatch.config import RATE_LIMIT_REPORTS, RATE_LIMIT_WINDOW_SECONDS
from notifications.services import notify_critical_report
from .forms import OfficerReportForm, PublicReportForm, TrackingForm
from .models import Report, ReportActivity
from .services import assess_authorized_site, calculate_risk, find_duplicate, transition_report

def _rate_key(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    return "report-rate:" + (forwarded or request.META.get("REMOTE_ADDR", "unknown"))

@require_http_methods(["GET", "POST"])
def submit_report(request):
    form = PublicReportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        key = _rate_key(request); count = cache.get(key, 0)
        if count >= RATE_LIMIT_REPORTS:
            form.add_error(None, "Too many recent submissions. Please try again later.")
        else:
            report = form.save(commit=False); report.source = Report.Source.PUBLIC; report.save()
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
