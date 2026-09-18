from accounts.models import User
from .models import Notification

def create_notification(recipient, title, message, url="", event_key=""):
    return Notification.objects.create(recipient=recipient, title=title, message=message, url=url, event_key=event_key)

def notify_critical_report(report):
    users = User.objects.filter(is_active=True, role__in=[User.Role.SYSTEM_ADMIN, User.Role.COUNTY_ADMIN, User.Role.OFFICER]).filter(county__in=[report.county, None])
    for user in users: create_notification(user, "Critical-risk report", f"{report.reference_code} requires prompt review.", f"/reports/case/{report.reference_code}/", "critical-report")

