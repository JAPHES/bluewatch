from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.access import roles_required
from notifications.services import create_notification
from reports.models import MarineImpactRecord, Report, ReportActivity
from reports.services import transition_report
from .forms import AssignmentForm, AssignmentUpdateForm
from .models import CleanupAssignment

def _can_access(user, assignment):
    if user.has_role("system_admin","county_admin","officer"): return not user.county_id or user.county_id==assignment.report.county_id
    return user.role=="team_member" and assignment.assigned_team.members.filter(pk=user.pk).exists()

@roles_required("system_admin","county_admin","officer")
def create_assignment(request):
    form=AssignmentForm(request.POST or None,user=request.user)
    if request.method=="POST" and form.is_valid():
        item=form.save(commit=False); item.assigned_officer=request.user; item.save()
        if item.report.verification_status != Report.Verification.VERIFIED:
            item.delete(); form.add_error("report","Only verified reports can be assigned.")
        else:
            if item.report.operational_status==Report.Status.VERIFIED: transition_report(item.report,Report.Status.ASSIGNED,request.user,"Cleanup assignment created")
            for member in item.assigned_team.members.all(): create_notification(member,"Cleanup assignment created",f"You have been assigned {item.report.reference_code}.",f"/operations/{item.pk}/","assignment-created")
            messages.success(request,"Cleanup assignment created."); return redirect("operations:detail",pk=item.pk)
    return render(request,"operations/form.html",{"form":form})

@roles_required("system_admin","county_admin","officer","team_member")
def assignment_detail(request,pk):
    item=get_object_or_404(CleanupAssignment,pk=pk)
    if not _can_access(request.user,item): raise PermissionDenied
    form=AssignmentUpdateForm(request.POST or None,request.FILES or None,instance=item)
    if request.method=="POST" and form.is_valid():
        previous=item.assignment_status; item=form.save()
        ReportActivity.objects.create(report=item.report,action="Cleanup assignment updated",previous_value=previous,new_value=item.assignment_status,responsible_user=request.user,note=item.completion_notes)
        if item.assignment_status==CleanupAssignment.Status.IN_PROGRESS and item.report.operational_status==Report.Status.ASSIGNED: transition_report(item.report,Report.Status.IN_PROGRESS,request.user,"Cleanup started")
        if item.assignment_status==CleanupAssignment.Status.SUBMITTED:
            create_notification(item.assigned_officer,"Cleanup awaiting verification",f"Evidence for {item.report.reference_code} is ready.",f"/operations/{item.pk}/","cleanup-submitted")
        messages.success(request,"Assignment updated."); return redirect("operations:detail",pk=pk)
    return render(request,"operations/detail.html",{"assignment":item,"form":form})

@roles_required("system_admin","county_admin","officer")
@require_POST
def verify_assignment(request,pk):
    item=get_object_or_404(CleanupAssignment,pk=pk)
    if request.user.county_id and item.report.county_id!=request.user.county_id and not request.user.is_superuser: raise PermissionDenied
    if item.assignment_status!=CleanupAssignment.Status.SUBMITTED or not item.after_photo:
        messages.error(request,"Submitted cleanup evidence, including an after photo, is required.")
    else:
        item.assignment_status=CleanupAssignment.Status.COMPLETED; item.verified_by=request.user; item.verified_at=timezone.now(); item.save()
        if item.report.operational_status==Report.Status.IN_PROGRESS: transition_report(item.report,Report.Status.CLEANED,request.user,"Cleanup evidence verified")
        MarineImpactRecord.objects.update_or_create(report=item.report,defaults={"waste_removed_kg":item.estimated_waste_collected_kg or 0,"recycled_kg":item.waste_diverted_for_recycling_kg,"high_risk_near_water_resolved":item.report.risk_level in [Report.Risk.HIGH,Report.Risk.CRITICAL] and item.report.proximity_to_water in [Report.Water.IN_WATER,Report.Water.UNDER_50,Report.Water.UNDER_200]})
        messages.success(request,"Cleanup evidence verified.")
    return redirect("operations:detail",pk=pk)
