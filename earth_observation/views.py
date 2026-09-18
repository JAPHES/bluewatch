import json
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.access import roles_required
from reports.models import Report, ReportActivity
from reports.services import assess_authorized_site, calculate_risk, find_duplicate
from .forms import AreaForm, CandidateForm, CandidateReportForm, CandidateReviewForm, SurveyForm
from .models import AreaOfInterest, ObservationCandidate, ObservationSurvey
from .services import point_in_polygon

EO_ROLES = ("system_admin", "county_admin", "officer", "analyst")


def _county_allowed(user, county_id):
    return user.is_superuser or not user.county_id or user.county_id == county_id


def _area_for_user(request, pk):
    area = get_object_or_404(AreaOfInterest.objects.select_related("county", "ward"), pk=pk, is_active=True)
    if not _county_allowed(request.user, area.county_id): raise PermissionDenied
    return area


def _survey_for_user(request, pk):
    survey = get_object_or_404(ObservationSurvey.objects.select_related("area__county", "area__ward"), pk=pk)
    if not _county_allowed(request.user, survey.area.county_id): raise PermissionDenied
    return survey


@roles_required(*EO_ROLES)
def workspace(request):
    areas = AreaOfInterest.objects.filter(is_active=True).select_related("county", "ward")
    surveys = ObservationSurvey.objects.select_related("area", "area__county")
    if request.user.county_id and not request.user.is_superuser:
        areas = areas.filter(county=request.user.county)
        surveys = surveys.filter(area__county=request.user.county)
    return render(request, "earth_observation/workspace.html", {"areas": areas, "surveys": surveys[:15]})


@roles_required(*EO_ROLES)
def create_area(request):
    form = AreaForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        area = form.save(commit=False); area.created_by = request.user; area.save()
        messages.success(request, "Area of interest saved. You can now start an imagery survey.")
        return redirect("earth_observation:area", pk=area.pk)
    return render(request, "earth_observation/area_form.html", {"form": form})


@roles_required(*EO_ROLES)
def area_detail(request, pk):
    area = _area_for_user(request, pk)
    form = SurveyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        survey = form.save(commit=False); survey.area = area; survey.requested_by = request.user
        survey.status = ObservationSurvey.Status.READY; survey.save()
        messages.success(request, "Survey created. Review the imagery and map suspected sites.")
        return redirect("earth_observation:survey", pk=survey.pk)
    resident_reports = Report.objects.filter(county=area.county, is_archived=False)
    markers = [{"ref": r.reference_code, "lat": float(r.latitude), "lng": float(r.longitude), "risk": r.risk_level, "status": r.get_operational_status_display()} for r in resident_reports]
    return render(request, "earth_observation/area_detail.html", {"area": area, "form": form, "boundary_json": json.dumps(area.boundary), "reports_json": json.dumps(markers)})


@roles_required(*EO_ROLES)
def survey_detail(request, pk):
    survey = _survey_for_user(request, pk)
    if survey.status == ObservationSurvey.Status.READY:
        survey.status = ObservationSurvey.Status.IN_REVIEW; survey.save(update_fields=["status", "updated_at"])
    candidate_form = CandidateForm()
    candidates = survey.candidates.select_related("suggested_category", "linked_report")
    resident_reports = Report.objects.filter(county=survey.area.county, is_archived=False)
    candidate_markers = [{"id": c.pk, "lat": float(c.latitude), "lng": float(c.longitude), "status": c.review_status, "source": c.get_detection_source_display()} for c in candidates]
    report_markers = [{"ref": r.reference_code, "lat": float(r.latitude), "lng": float(r.longitude), "risk": r.risk_level} for r in resident_reports]
    context = {
        "survey": survey, "candidate_form": candidate_form, "candidates": candidates,
        "boundary_json": json.dumps(survey.area.boundary), "candidates_json": json.dumps(candidate_markers),
        "reports_json": json.dumps(report_markers),
    }
    return render(request, "earth_observation/survey_detail.html", context)


@roles_required(*EO_ROLES)
@require_POST
def add_candidate(request, pk):
    survey = _survey_for_user(request, pk)
    form = CandidateForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        if not point_in_polygon(item.latitude, item.longitude, survey.area.boundary):
            messages.error(request, "The candidate must be inside the selected area.")
        else:
            item.survey = survey; item.detection_source = ObservationCandidate.DetectionSource.HUMAN; item.save()
            messages.success(request, "Candidate mapped for human review.")
    else: messages.error(request, "Candidate could not be saved. Select a valid point and complete the form.")
    return redirect("earth_observation:survey", pk=survey.pk)


@roles_required(*EO_ROLES)
def candidate_detail(request, pk):
    candidate = get_object_or_404(ObservationCandidate.objects.select_related("survey__area__county", "suggested_category", "linked_report"), pk=pk)
    if not _county_allowed(request.user, candidate.survey.area.county_id): raise PermissionDenied
    review_form = CandidateReviewForm(request.POST or None, instance=candidate)
    if request.method == "POST" and "review" in request.POST and review_form.is_valid():
        item = review_form.save(commit=False); item.reviewed_by = request.user; item.save()
        messages.success(request, "Candidate review decision recorded.")
        return redirect("earth_observation:candidate", pk=item.pk)
    report_form = CandidateReportForm(county=candidate.survey.area.county, initial={
        "waste_category": candidate.suggested_category, "location_description": candidate.survey.area.name,
        "description": candidate.description, "date_observed": candidate.survey.imagery_capture_date or timezone.localdate(),
    })
    return render(request, "earth_observation/candidate_detail.html", {"candidate": candidate, "review_form": review_form, "report_form": report_form})


@roles_required("system_admin", "county_admin", "officer")
@require_POST
def convert_candidate(request, pk):
    candidate = get_object_or_404(ObservationCandidate.objects.select_related("survey__area__county"), pk=pk)
    if not _county_allowed(request.user, candidate.survey.area.county_id): raise PermissionDenied
    if candidate.review_status != ObservationCandidate.ReviewStatus.SUSPECTED or candidate.linked_report_id:
        messages.error(request, "Only a reviewed suspected candidate without a report can be converted.")
        return redirect("earth_observation:candidate", pk=pk)
    form = CandidateReportForm(request.POST, request.FILES, county=candidate.survey.area.county)
    if form.is_valid():
        with transaction.atomic():
            report = Report.objects.create(
                source=Report.Source.OFFICER, county=candidate.survey.area.county, ward=form.cleaned_data["ward"],
                location_description=form.cleaned_data["location_description"], latitude=candidate.latitude,
                longitude=candidate.longitude, original_image=form.cleaned_data["original_image"],
                waste_category=form.cleaned_data["waste_category"], estimated_size=form.cleaned_data["estimated_size"],
                proximity_to_water=form.cleaned_data["proximity_to_water"], description=form.cleaned_data["description"],
                date_observed=form.cleaned_data["date_observed"], assigned_officer=request.user,
                verification_status=Report.Verification.PENDING, operational_status=Report.Status.REVIEW,
                analysis_status=Report.Analysis.HUMAN_REVIEW,
                analysis_notes=f"Created from earth-observation survey {candidate.survey_id}; requires field/officer verification.",
            )
            assess_authorized_site(report); report.possible_duplicate_of = find_duplicate(report)
            report.risk_score, report.risk_level = calculate_risk(report)
            report.save()
            candidate.linked_report = report; candidate.review_status = ObservationCandidate.ReviewStatus.REPORT_CREATED
            candidate.reviewed_by = request.user; candidate.save(update_fields=["linked_report", "review_status", "reviewed_by", "updated_at"])
            ReportActivity.objects.create(report=report, action="Created from mapped satellite-imagery candidate", new_value=report.operational_status, responsible_user=request.user, note=f"Survey {candidate.survey_id}; human verification still required.")
        messages.success(request, f"Operational report {report.reference_code} created for verification.")
        return redirect("reports:detail", reference_code=report.reference_code)
    review_form = CandidateReviewForm(instance=candidate)
    return render(request, "earth_observation/candidate_detail.html", {"candidate": candidate, "review_form": review_form, "report_form": form}, status=400)


@roles_required(*EO_ROLES)
@require_POST
def complete_survey(request, pk):
    survey = _survey_for_user(request, pk)
    survey.status = ObservationSurvey.Status.COMPLETED; survey.reviewed_by = request.user
    survey.completed_at = timezone.now(); survey.save(update_fields=["status", "reviewed_by", "completed_at", "updated_at"])
    messages.success(request, "Survey review marked complete.")
    return redirect("earth_observation:survey", pk=pk)
