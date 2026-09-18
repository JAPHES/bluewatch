from django.contrib import admin
from .models import AuthorizedSite,County,PlatformSetting,SensitiveLocation,Ward
@admin.register(County)
class CountyAdmin(admin.ModelAdmin): list_display=("name","code","is_coastal","is_active"); search_fields=("name","code"); list_filter=("is_active","is_coastal")
@admin.register(Ward)
class WardAdmin(admin.ModelAdmin): list_display=("name","county","is_active"); list_filter=("county","is_active"); search_fields=("name",)
@admin.register(AuthorizedSite)
class AuthorizedSiteAdmin(admin.ModelAdmin): list_display=("name","county","ward","site_type","operating_status","is_active"); list_filter=("county","operating_status","is_active"); search_fields=("name","managing_organization")
@admin.register(SensitiveLocation)
class SensitiveLocationAdmin(admin.ModelAdmin): list_display=("name","location_type","county","protection_radius_m","is_active"); list_filter=("location_type","county","is_active"); search_fields=("name",)
@admin.register(PlatformSetting)
class SettingAdmin(admin.ModelAdmin): list_display=("key","value","updated_at"); search_fields=("key","description"); readonly_fields=("updated_at",)

