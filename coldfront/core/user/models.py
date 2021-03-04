from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)
    


class UserDataUsage(models.Model):
    # user = models.ForeignKey(User)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    usage = models.FloatField()
    # project = models.CharField(Project, on_delete=models.CASCADE)
    # project = models.OneToOneField(project) # either or;

