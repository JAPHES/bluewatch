from django.contrib import admin
from .models import CleanupAssignment,CleanupTeam
@admin.register(CleanupTeam)
class TeamAdmin(admin.ModelAdmin): list_display=("name","county","is_active"); list_filter=("county","is_active"); search_fields=("name",); filter_horizontal=("members",)
@admin.register(CleanupAssignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display=("report","assigned_team","priority","scheduled_cleanup_date","assignment_status","verified_by")
    list_filter=("priority","assignment_status","assigned_team__county"); search_fields=("report__reference_code","assigned_team__name"); date_hierarchy="scheduled_cleanup_date"
    autocomplete_fields=("report","assigned_team","assigned_officer","verified_by"); readonly_fields=("created_at","updated_at","verified_at")

