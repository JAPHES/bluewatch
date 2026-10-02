from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from accounts.access import roles_required
from .forms import GovernmentUserForm, ProfileForm

@login_required
def profile(request):
    form=ProfileForm(request.POST or None,instance=request.user)
    if request.method=="POST" and form.is_valid(): form.save(); messages.success(request,"Profile updated."); return redirect("accounts:profile")
    return render(request,"accounts/profile.html",{"form":form})

@roles_required("system_admin","county_admin")
def create_user(request):
    form=GovernmentUserForm(request.POST or None, actor=request.user)
    if request.method=="POST" and form.is_valid():
        form.save()
        messages.success(request,"Staff account created. They can sign in using their email address.")
        return redirect("dashboard:county")
    return render(request,"accounts/create_user.html",{"form":form})
