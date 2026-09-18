from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Notification

@login_required
def notification_list(request): return render(request, "notifications/list.html", {"notifications": request.user.notifications.all()})
@login_required
@require_POST
def mark_read(request, pk):
    item = get_object_or_404(Notification, pk=pk, recipient=request.user); item.is_read=True; item.save(update_fields=["is_read"])
    return redirect(item.url or "notifications:list")
@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications:list")

