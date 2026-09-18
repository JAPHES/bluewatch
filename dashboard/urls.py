from django.urls import path
from . import views
app_name="dashboard"
urlpatterns=[path("",views.home,name="home"),path("county/",views.county_dashboard,name="county"),path("team/",views.team_dashboard,name="team"),path("impact/",views.public_dashboard,name="public")]
