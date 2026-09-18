from django.contrib import admin
from .models import Notification,NotificationTemplate
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin): list_display=("recipient","title","event_key","is_read","created_at"); list_filter=("event_key","is_read"); search_fields=("recipient__username","title","message"); date_hierarchy="created_at"; readonly_fields=("created_at",)
@admin.register(NotificationTemplate)
class TemplateAdmin(admin.ModelAdmin): list_display=("event_key","title_template","is_active"); list_filter=("is_active",)
