from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.models import Notification
from operations.models import CleanupAssignment

class Command(BaseCommand):
    help="Create idempotent approaching-due and overdue in-system notifications. Schedule daily in production."
    def handle(self,*args,**kwargs):
        today=timezone.localdate(); active=CleanupAssignment.objects.exclude(assignment_status__in=["completed","cancelled"])
        for item in active:
            event="assignment-overdue" if item.scheduled_cleanup_date<today else "assignment-due" if item.scheduled_cleanup_date<=today+timedelta(days=2) else None
            if not event: continue
            recipients=list(item.assigned_team.members.all())+[item.assigned_officer]
            for user in set(recipients): Notification.objects.get_or_create(recipient=user,event_key=f"{event}-{item.pk}-{today}",defaults={"title":"Assignment overdue" if event=="assignment-overdue" else "Assignment approaching due date","message":f"{item.report.reference_code} is scheduled for {item.scheduled_cleanup_date}.","url":f"/operations/{item.pk}/"})
        self.stdout.write(self.style.SUCCESS("Due-assignment notifications updated."))
