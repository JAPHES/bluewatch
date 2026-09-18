from django.contrib import admin
from .models import MarineImpactRecord,Report,ReportActivity,WasteCategory
class ActivityInline(admin.TabularInline): model=ReportActivity; extra=0; can_delete=False; readonly_fields=("action","previous_value","new_value","responsible_user","note","timestamp")
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display=("reference_code","county","ward","waste_category","verification_status","operational_status","risk_level","date_submitted")
    list_filter=("county","verification_status","operational_status","risk_level","waste_category","is_archived")
    search_fields=("reference_code","location_description","description"); date_hierarchy="date_submitted"
    readonly_fields=("reference_code","date_submitted","created_at","updated_at","risk_score","near_authorized_site","authorized_site_note")
    autocomplete_fields=("county","ward","waste_category","assigned_officer","possible_duplicate_of")
    inlines=(ActivityInline,)
    fieldsets=(("Case",{"fields":("reference_code","source","county","ward","location_description","latitude","longitude","original_image","waste_category","estimated_size","proximity_to_water","description","date_observed")}),
        ("Workflow",{"fields":("verification_status","operational_status","risk_score","risk_level","assigned_officer","possible_duplicate_of","near_authorized_site","authorized_site_note","is_archived")}),
        ("Private reporter data",{"classes":("collapse",),"fields":("reporter_name","reporter_phone","reporter_email")}),
        ("Future analysis",{"classes":("collapse",),"fields":("analysis_status","analysis_confidence","suggested_category","analysis_notes")}),
        ("Audit",{"fields":("date_submitted","created_at","updated_at")}))
    def has_delete_permission(self,request,obj=None): return False
@admin.register(WasteCategory)
class CategoryAdmin(admin.ModelAdmin): list_display=("name","risk_weight","hazardous","is_active"); list_filter=("hazardous","is_active"); search_fields=("name",); prepopulated_fields={"slug":("name",)}
@admin.register(ReportActivity)
class ActivityAdmin(admin.ModelAdmin): list_display=("report","action","responsible_user","timestamp"); list_filter=("action",); search_fields=("report__reference_code","note"); readonly_fields=("report","action","previous_value","new_value","responsible_user","note","timestamp")
@admin.register(MarineImpactRecord)
class ImpactAdmin(admin.ModelAdmin): list_display=("report","waste_removed_kg","recycled_kg","high_risk_near_water_resolved","recorded_at"); readonly_fields=("recorded_at",)
