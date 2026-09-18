from django.urls import path
from . import views
app_name="core"
urlpatterns=[path("",views.home,name="home"),path("about/",views.about,name="about"),path("how-it-works/",views.how_it_works,name="how"),path("contact/",views.contact,name="contact"),path("health/",views.health,name="health")]
