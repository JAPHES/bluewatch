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
    form=GovernmentUserForm(request.POST or None)
    if request.user.role=="county_admin" and not request.user.is_superuser:
        allowed={"officer","team_member","analyst"}
        form.fields["role"].choices=[choice for choice in form.fields["role"].choices if choice[0] in allowed]
        form.fields["county"].disabled=True
        form.fields["county"].initial=request.user.county
    if request.method=="POST" and form.is_valid():
        user=form.save(commit=False)
        if request.user.role=="county_admin": user.county=request.user.county
        user.save(); messages.success(request,"Government account created."); return redirect("dashboard:county")
    return render(request,"accounts/create_user.html",{"form":form})
