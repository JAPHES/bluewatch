from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls), path("", include("core.urls")),
    path("accounts/", include("accounts.urls")), path("reports/", include("reports.urls")),
    path("operations/", include("operations.urls")), path("dashboard/", include("dashboard.urls")),
    path("notifications/", include("notifications.urls")),
    path("earth-observation/", include("earth_observation.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
admin.site.site_header = "BlueWatch Administration"
admin.site.site_title = "BlueWatch Admin"
admin.site.index_title = "Platform management"
