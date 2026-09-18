from django.urls import path
from . import views
app_name="operations"
urlpatterns=[path("new/",views.create_assignment,name="create"),path("<int:pk>/",views.assignment_detail,name="detail"),path("<int:pk>/verify/",views.verify_assignment,name="verify")]
