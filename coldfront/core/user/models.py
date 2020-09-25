from django.contrib.auth.models import User

from django.db import models
from rest_framework.authtoken.models import Token


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)


class ExpiringToken(Token):
    expiration = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Expiring Token'
