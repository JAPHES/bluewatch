import json
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect, render
from django.utils import timezone
from accounts.access import roles_required
from operations.models import CleanupAssignment
from reports.models import MarineImpactRecord, Report

@login_required
def home(request):
    if request.user.role=="team_member": return redirect("dashboard:team")
    return redirect("dashboard:county")

def _county_reports(request):
    qs=Report.objects.filter(is_archived=False).select_related("county","ward","waste_category")
    if request.user.county_id and not request.user.is_superuser: qs=qs.filter(county=request.user.county)
    params={"county":"county_id","ward":"ward_id","status":"operational_status","risk":"risk_level","category":"waste_category_id"}
    for key,field in params.items():
        if request.GET.get(key): qs=qs.filter(**{field:request.GET[key]})
    if request.GET.get("date_from"): qs=qs.filter(date_submitted__date__gte=request.GET["date_from"])
    if request.GET.get("date_to"): qs=qs.filter(date_submitted__date__lte=request.GET["date_to"])
    return qs

@roles_required("system_admin","county_admin","officer","analyst")
def county_dashboard(request):
    qs=_county_reports(request); assignments=CleanupAssignment.objects.filter(report__in=qs)
    avg=assignments.filter(start_time__isnull=False).aggregate(value=Avg(F("start_time")-F("created_at")))["value"]
    category=list(qs.values("waste_category__name").annotate(total=Count("id")).order_by("-total"))
    risk=list(qs.values("risk_level").annotate(total=Count("id")))
    monthly=list(qs.annotate(month=TruncMonth("date_submitted")).values("month").annotate(total=Count("id")).order_by("month"))
    markers=[{"ref":r.reference_code,"lat":float(r.latitude),"lng":float(r.longitude),"risk":r.risk_level,"status":r.get_operational_status_display()} for r in qs[:500]]
    metrics={"total":qs.count(),"pending":qs.filter(verification_status="pending").count(),"verified":qs.filter(verification_status="verified").count(),"critical":qs.filter(risk_level="critical").count(),"assigned":qs.filter(operational_status="assigned").count(),"cleaned":qs.filter(operational_status="cleaned").count(),"closed":qs.filter(operational_status="closed").count(),"average_response":round(avg.total_seconds()/3600,1) if avg else None}
    overdue=assignments.filter(scheduled_cleanup_date__lt=timezone.localdate()).exclude(assignment_status__in=["completed","cancelled"])
    hotspots=list(qs.values("ward__name").annotate(total=Count("id")).filter(total__gte=2).order_by("-total")[:5])
    return render(request,"dashboard/county.html",{"reports":qs[:20],"metrics":metrics,"overdue":overdue,"hotspots":hotspots,"category_json":json.dumps(category),"risk_json":json.dumps(risk),"monthly_json":json.dumps(monthly,default=str),"markers_json":json.dumps(markers)})

@roles_required("system_admin","county_admin","officer","team_member")
def team_dashboard(request):
    qs=CleanupAssignment.objects.select_related("report","assigned_team")
    if request.user.role=="team_member": qs=qs.filter(assigned_team__members=request.user)
    elif request.user.county_id: qs=qs.filter(report__county=request.user.county)
    groups={"new":qs.filter(assignment_status="new"),"scheduled":qs.filter(assignment_status="scheduled"),"in_progress":qs.filter(assignment_status="in_progress"),"overdue":qs.filter(scheduled_cleanup_date__lt=timezone.localdate()).exclude(assignment_status__in=["completed","cancelled"]),"completed":qs.filter(assignment_status="completed")}
    return render(request,"dashboard/team.html",{"assignments":qs,"groups":groups})

def public_dashboard(request):
    reports=Report.objects.filter(verification_status="verified",is_archived=False)
    impacts=MarineImpactRecord.objects.all()
    monthly=list(reports.filter(operational_status__in=["cleaned","closed"]).annotate(month=TruncMonth("updated_at")).values("month").annotate(total=Count("id")).order_by("month"))
    categories=list(reports.values("waste_category__name").annotate(total=Count("id")).order_by("-total"))
    markers=[{"lat":round(float(r.latitude),3),"lng":round(float(r.longitude),3),"risk":r.risk_level,"county":r.county.name} for r in reports.select_related("county")[:500]]
    metrics={"verified":reports.count(),"cleaned":reports.filter(operational_status__in=["cleaned","closed"]).count(),"removed":impacts.aggregate(x=Sum("waste_removed_kg"))["x"] or 0,"recycled":impacts.aggregate(x=Sum("recycled_kg"))["x"] or 0,"water_resolved":impacts.filter(high_risk_near_water_resolved=True).count()}
    return render(request,"dashboard/public.html",{"metrics":metrics,"monthly_json":json.dumps(monthly,default=str),"category_json":json.dumps(categories),"markers_json":json.dumps(markers)})

