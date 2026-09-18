from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
@admin.register(User)
class BlueWatchUserAdmin(UserAdmin):
    list_display=("username","email","role","county","is_active","is_staff")
    list_filter=("role","county","is_active","is_staff")
    search_fields=("username","first_name","last_name","email")
    fieldsets=UserAdmin.fieldsets+(("BlueWatch profile",{"fields":("role","county","phone","job_title")}),)
    add_fieldsets=UserAdmin.add_fieldsets+(("BlueWatch profile",{"fields":("role","county","email")}),)

