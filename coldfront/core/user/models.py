from django.contrib.auth.models import User
from django.db import models
from coldfront.core.project.models import Project


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)
    


class UserDataUsage(models.Model):
    # user = models.ForeignKey(User)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    usage = models.FloatField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE,)
    
