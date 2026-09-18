from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from .validators import normalize_username_spaces

class ProfileForm(forms.ModelForm):
    class Meta: model=User; fields=["first_name","last_name","email","phone","job_title"]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values(): field.widget.attrs["class"]="form-control"

class GovernmentUserForm(UserCreationForm):
    class Meta: model=User; fields=["username","first_name","last_name","email","role","county"]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values(): field.widget.attrs["class"]="form-control"
    def clean_username(self):
        return normalize_username_spaces(super().clean_username())
