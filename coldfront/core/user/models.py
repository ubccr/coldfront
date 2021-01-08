from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator
from django.db import models
from rest_framework.authtoken.models import Token


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_pi = models.BooleanField(default=False)

    middle_name = models.CharField(max_length=30, blank=True)
    cluster_uid = models.CharField(
        unique=True,
        max_length=10,
        validators=[
            MinLengthValidator(3),
            RegexValidator(
                regex=r'^[0-9]+$', message='Cluster UID must be numeric.')
        ],
        blank=True,
        null=True
    )

    access_agreement_signed_date = models.DateTimeField(blank=True, null=True)


class ExpiringToken(Token):
    expiration = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Expiring Token'
