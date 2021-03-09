from django.contrib.auth.models import User
from django.db import models
from coldfront.core.project.models import Project


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)
    
