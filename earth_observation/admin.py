from django.contrib import admin
from .models import AreaOfInterest, ObservationCandidate, ObservationSurvey


@admin.register(AreaOfInterest)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "county", "ward", "created_by", "is_active", "updated_at")
    list_filter = ("county", "is_active")
    search_fields = ("name", "description")
    autocomplete_fields = ("county", "ward", "created_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ObservationSurvey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("title", "area", "method", "status", "imagery_capture_date", "requested_by", "created_at")
    list_filter = ("method", "status", "area__county")
    search_fields = ("title", "area__name", "imagery_source", "provider_job_id")
    autocomplete_fields = ("area", "requested_by", "reviewed_by")
    readonly_fields = ("created_at", "updated_at", "completed_at")
    date_hierarchy = "created_at"


@admin.register(ObservationCandidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("id", "survey", "detection_source", "review_status", "suggested_category", "linked_report", "created_at")
    list_filter = ("detection_source", "review_status", "survey__area__county")
    search_fields = ("survey__title", "description", "linked_report__reference_code")
    autocomplete_fields = ("survey", "suggested_category", "reviewed_by", "linked_report")
    readonly_fields = ("created_at", "updated_at")
