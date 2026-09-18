from django.urls import path
from . import views

app_name = "earth_observation"
urlpatterns = [
    path("", views.workspace, name="workspace"),
    path("areas/new/", views.create_area, name="create_area"),
    path("areas/<int:pk>/", views.area_detail, name="area"),
    path("surveys/<int:pk>/", views.survey_detail, name="survey"),
    path("surveys/<int:pk>/candidates/new/", views.add_candidate, name="add_candidate"),
    path("surveys/<int:pk>/complete/", views.complete_survey, name="complete_survey"),
    path("candidates/<int:pk>/", views.candidate_detail, name="candidate"),
    path("candidates/<int:pk>/convert/", views.convert_candidate, name="convert_candidate"),
]
