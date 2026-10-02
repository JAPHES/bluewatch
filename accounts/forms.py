from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q
from locations.models import County
from .models import User

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "job_title"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uses_email_login = bool(self.instance.pk and self.instance.username == self.instance.email)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        if self._uses_email_login:
            self.fields["email"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if email and len(email) > User._meta.get_field("username").max_length:
            raise ValidationError("Use an email address of 150 characters or fewer.")
        if email and User.objects.exclude(pk=self.instance.pk).filter(
            Q(email__iexact=email) | Q(username__iexact=email)
        ).exists():
            raise ValidationError("An account already uses this email address.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        if self._uses_email_login:
            user.username = user.email
        if commit:
            user.save()
            self.save_m2m()
        return user

class StaffLoginForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get("username", "")
        if "@" in username:
            self.cleaned_data["username"] = username.strip().lower()
        return super().clean()


class GovernmentUserForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "role", "county"]
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        for name in ("first_name", "last_name", "email", "role"):
            self.fields[name].required = True
        allowed = {User.Role.OFFICER, User.Role.TEAM_MEMBER, User.Role.ANALYST}
        if actor.is_superuser or actor.role == User.Role.SYSTEM_ADMIN:
            allowed = set(User.Role.values)
        self.fields["role"].choices = [("", "Select a role")] + [
            choice for choice in User.Role.choices if choice[0] in allowed
        ]
        if actor.county_id:
            self.fields.pop("county")
        elif actor.is_superuser or actor.role == User.Role.SYSTEM_ADMIN:
            self.fields["county"].queryset = County.objects.filter(is_active=True)
            self.fields["county"].empty_label = "Select a county"
        else:
            self.fields.pop("county")
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"

    def clean_first_name(self):
        value = self.cleaned_data["first_name"].strip()
        if not value:
            raise ValidationError("Enter a first name.")
        return value

    def clean_last_name(self):
        value = self.cleaned_data["last_name"].strip()
        if not value:
            raise ValidationError("Enter a last name.")
        return value

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if len(email) > User._meta.get_field("username").max_length:
            raise ValidationError("Use an email address of 150 characters or fewer.")
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            raise ValidationError("An account already uses this email address.")
        return email

    def clean(self):
        cleaned = super().clean()
        if self.actor.role == User.Role.COUNTY_ADMIN and not self.actor.county_id and not self.actor.is_superuser:
            self.add_error(None, "Your administrator account needs a county before you can add staff.")
        if "county" in self.fields and cleaned.get("role") != User.Role.SYSTEM_ADMIN and not cleaned.get("county"):
            self.add_error("county", "Select the county this staff member will work in.")
        password = cleaned.get("password")
        if password:
            candidate = User(
                username=cleaned.get("email", ""),
                email=cleaned.get("email", ""),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
            )
            try:
                validate_password(password, user=candidate)
            except ValidationError as exc:
                self.add_error("password", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        user.county = self.actor.county if self.actor.county_id else self.cleaned_data.get("county")
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
