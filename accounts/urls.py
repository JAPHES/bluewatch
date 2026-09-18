from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views
app_name="accounts"
urlpatterns=[
 path("login/",auth_views.LoginView.as_view(template_name="accounts/login.html"),name="login"),
 path("logout/",auth_views.LogoutView.as_view(),name="logout"), path("profile/",views.profile,name="profile"),
 path("password/",auth_views.PasswordChangeView.as_view(template_name="accounts/password_change.html",success_url=reverse_lazy("accounts:profile")),name="password_change"),
 path("users/new/",views.create_user,name="create_user")]

