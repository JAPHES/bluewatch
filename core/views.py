from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from reports.models import MarineImpactRecord, Report

def home(request):
    stats={"verified":Report.objects.filter(verification_status="verified").count(),"cleaned":Report.objects.filter(operational_status__in=["cleaned","closed"]).count(),"waste":sum(x.waste_removed_kg for x in MarineImpactRecord.objects.all())}
    return render(request,"core/home.html",{"stats":stats})
def about(request): return render(request,"core/about.html")
def how_it_works(request): return render(request,"core/how.html")
def contact(request): return render(request,"core/contact.html")
def health(request):
    try:
        with connection.cursor() as cursor: cursor.execute("SELECT 1")
        return JsonResponse({"status":"ok","database":"ok"})
    except Exception: return JsonResponse({"status":"degraded"},status=503)

