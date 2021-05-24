from django.conf import settings
from django.db import models
from coldfront.core.project.models import Project


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)

