from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from .validators import BlueWatchUsernameValidator, normalize_username_spaces


class BlueWatchUserManager(UserManager):
    def _create_user(self, username, email, password, **extra_fields):
        username = normalize_username_spaces(username)
        return super()._create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    username_validator = BlueWatchUsernameValidator()
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_("Required. 150 characters or fewer. Letters, numbers, spaces and @/./+/-/_ only."),
        validators=[username_validator],
        error_messages={"unique": _("A user with that username already exists.")},
    )
    class Role(models.TextChoices):
        SYSTEM_ADMIN = "system_admin", "System Administrator"
        COUNTY_ADMIN = "county_admin", "County Administrator"
        OFFICER = "officer", "Waste Management Officer"
        TEAM_MEMBER = "team_member", "Cleanup Team Member"
        ANALYST = "analyst", "Environmental Analyst"
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.OFFICER)
    county = models.ForeignKey("locations.County", null=True, blank=True, on_delete=models.SET_NULL, related_name="users")
    phone = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    objects = BlueWatchUserManager()

    def save(self, *args, **kwargs):
        self.username = normalize_username_spaces(self.username)
        super().save(*args, **kwargs)

    def has_role(self, *roles):
        return self.is_superuser or self.role in roles
