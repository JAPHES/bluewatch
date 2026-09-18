from django.conf import settings
from django.db import models

class NotificationTemplate(models.Model):
    event_key = models.SlugField(unique=True)
    title_template = models.CharField(max_length=160)
    message_template = models.TextField()
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.event_key

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=160)
    message = models.TextField()
    url = models.CharField(max_length=255, blank=True)
    event_key = models.SlugField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
    def __str__(self): return self.title
