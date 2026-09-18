"""Create repeatable, clearly fictional demonstration records."""
import base64, os
from datetime import timedelta
from decimal import Decimal
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from earth_observation.models import AreaOfInterest, ObservationCandidate, ObservationSurvey
from locations.models import AuthorizedSite, County, SensitiveLocation, Ward
from notifications.models import Notification, NotificationTemplate
from operations.models import CleanupAssignment, CleanupTeam
from reports.models import MarineImpactRecord, Report, ReportActivity, WasteCategory

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")

class Command(BaseCommand):
    help = "Seed realistic but fictional BlueWatch demonstration data (repeatable)."
    def handle(self, *args, **options):
        county_defs={"Mombasa":"001","Kwale":"002","Kilifi":"003","Lamu":"005","Tana River":"004"}
        counties={name:County.objects.update_or_create(name=name,defaults={"code":code,"is_coastal":True})[0] for name,code in county_defs.items()}
        ward_defs={"Mombasa":["Kisauni","Likoni","Mvita"],"Kwale":["Ukunda","Msambweni"],"Kilifi":["Kilifi North","Watamu"],"Lamu":["Lamu Island"],"Tana River":["Kipini"]}
        wards={}
        for cname,names in ward_defs.items():
            for name in names: wards[(cname,name)]=Ward.objects.get_or_create(county=counties[cname],name=name)[0]
        category_defs=[("Plastic waste",8,False),("Organic waste",4,False),("Mixed household waste",8,False),("Construction waste",7,False),("Electronic waste",18,True),("Metal waste",5,False),("Glass",8,True),("Medical or hazardous-looking waste",30,True),("Other",5,False)]
        categories={}
        from django.utils.text import slugify
        for name,weight,hazard in category_defs: categories[name]=WasteCategory.objects.update_or_create(slug=slugify(name),defaults={"name":name,"risk_weight":weight,"hazardous":hazard})[0]
        AuthorizedSite.objects.update_or_create(name="Demo Mombasa Recovery Yard",defaults={"county":counties["Mombasa"],"ward":wards[("Mombasa","Kisauni")],"site_type":"Material recovery facility","latitude":Decimal("-4.010000"),"longitude":Decimal("39.690000"),"description":"Fictional demonstration facility.","managing_organization":"Demo Coastal Services"})
        sensitive=[("Tudor Creek Demo Zone","mangrove","Mombasa",-4.03,39.66,800),("Likoni Beach Demo Zone","beach","Mombasa",-4.09,39.66,600),("Kilifi Creek Demo Zone","river","Kilifi",-3.63,39.85,800),("Kisauni Demo School","school","Mombasa",-4.02,39.69,300)]
        for name,kind,cname,lat,lng,radius in sensitive: SensitiveLocation.objects.update_or_create(name=name,defaults={"location_type":kind,"county":counties[cname],"latitude":lat,"longitude":lng,"protection_radius_m":radius,"description":"Fictional demonstration location."})
        password=os.getenv("BLUEWATCH_DEMO_PASSWORD","")
        user_defs=[("bw_admin","system_admin",None),("mombasa_officer","officer",counties["Mombasa"]),("mombasa_county_admin","county_admin",counties["Mombasa"]),("coastal_analyst","analyst",counties["Mombasa"]),("cleanup_member","team_member",counties["Mombasa"])]
        users={}
        for username,role,county in user_defs:
            user,created=User.objects.get_or_create(username=username,defaults={"role":role,"county":county,"first_name":"Demo","last_name":role.replace("_"," ").title(),"email":f"{username}@example.invalid","is_staff":role=="system_admin"})
            user.role=role; user.county=county
            if password: user.set_password(password)
            elif created: user.set_unusable_password()
            user.save(); users[username]=user
        team,_=CleanupTeam.objects.update_or_create(name="Demo Mombasa Coastal Crew",defaults={"county":counties["Mombasa"],"contact_phone":"+254 700 000 000"}); team.members.add(users["cleanup_member"])
        samples=[("BW-DEMO-001","Kisauni",-4.031,39.681,"Plastic waste","large","under_50","verified","assigned",58,"high"),("BW-DEMO-002","Likoni",-4.088,39.664,"Mixed household waste","extensive","in_water","verified","closed",82,"critical"),("BW-DEMO-003","Mvita",-4.060,39.668,"Construction waste","medium","over_200","pending","under_review",24,"moderate")]
        for i,(ref,ward,lat,lng,cat,size,water,verification,status,score,risk) in enumerate(samples):
            report,created=Report.objects.get_or_create(reference_code=ref,defaults={"source":"public","county":counties["Mombasa"],"ward":wards[("Mombasa",ward)],"location_description":f"Fictional landmark {i+1}","latitude":lat,"longitude":lng,"waste_category":categories[cat],"estimated_size":size,"proximity_to_water":water,"description":"Demonstration dumpsite record; not a real incident.","date_observed":timezone.localdate()-timedelta(days=12-i*3),"verification_status":verification,"operational_status":status,"risk_score":score,"risk_level":risk,"assigned_officer":users["mombasa_officer"]})
            if created: report.original_image.save(f"demo-{i}.png",ContentFile(PNG),save=True); ReportActivity.objects.create(report=report,action="Demo case created",new_value=status,note="Seeded fictional record")
            if ref=="BW-DEMO-001": CleanupAssignment.objects.get_or_create(report=report,defaults={"assigned_team":team,"assigned_officer":users["mombasa_officer"],"priority":"high","scheduled_cleanup_date":timezone.localdate()+timedelta(days=2),"instructions":"Remove waste safely and record disposal destination.","assignment_status":"scheduled"})
            if ref=="BW-DEMO-002": MarineImpactRecord.objects.update_or_create(report=report,defaults={"waste_removed_kg":850,"recycled_kg":240,"high_risk_near_water_resolved":True})
        templates=[("critical-report","Critical-risk report","Review {reference} promptly."),("assignment-created","Cleanup assignment created","Assignment for {reference} has been created."),("assignment-due","Assignment approaching due date","Assignment for {reference} is due soon."),("assignment-overdue","Assignment overdue","Assignment for {reference} is overdue."),("cleanup-submitted","Cleanup submitted for verification","Evidence for {reference} needs review."),("case-closed","Case closed","Case {reference} has been closed.")]
        for key,title,msg in templates: NotificationTemplate.objects.update_or_create(event_key=key,defaults={"title_template":title,"message_template":msg})
        Notification.objects.get_or_create(recipient=users["mombasa_officer"],event_key="critical-report",message="BW-DEMO-002 requires prompt review.",defaults={"title":"Critical-risk report","url":"/reports/case/BW-DEMO-002/"})
        area,_=AreaOfInterest.objects.update_or_create(
            county=counties["Mombasa"],name="Demo Tudor Creek observation area",
            defaults={"ward":wards[("Mombasa","Kisauni")],"boundary":{"type":"Polygon","coordinates":[[[39.640,-4.055],[39.700,-4.055],[39.700,-4.005],[39.640,-4.005],[39.640,-4.055]]]},"description":"Fictional area for demonstrating imagery review.","created_by":users["mombasa_officer"]})
        survey,_=ObservationSurvey.objects.update_or_create(
            area=area,title="Demo coastal imagery review",
            defaults={"imagery_source":"Configured satellite imagery basemap","method":"visual","status":"in_review","requested_by":users["mombasa_officer"]})
        ObservationCandidate.objects.get_or_create(
            survey=survey,latitude=Decimal("-4.035000"),longitude=Decimal("39.675000"),
            defaults={"detection_source":"human","suggested_category":categories["Plastic waste"],"description":"Fictional mapped candidate requiring human verification.","review_status":"unreviewed"})
        self.stdout.write(self.style.SUCCESS("BlueWatch demo data is ready."))
        if password: self.stdout.write("Demo users use BLUEWATCH_DEMO_PASSWORD from the environment.")
        else: self.stdout.write(self.style.WARNING("Demo users have unusable passwords. Run `python manage.py changepassword <username>` for each account you need."))
