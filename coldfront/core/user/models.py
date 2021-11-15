from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)
    department = models.CharField(max_length=100, default='')
    title = models.CharField(max_length=30, default='')
    max_projects = models.IntegerField(default=-1)
