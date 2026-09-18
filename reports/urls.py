from django.urls import path
from . import views
app_name = "reports"
urlpatterns = [path("new/", views.submit_report, name="submit"), path("confirmation/", views.confirmation, name="confirmation"), path("track/", views.track, name="track"), path("case/<str:reference_code>/", views.report_detail, name="detail"), path("case/<str:reference_code>/update/", views.update_report, name="update")]
