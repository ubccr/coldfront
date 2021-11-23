from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator
from django.db import models
from rest_framework.authtoken.models import Token

from phonenumber_field.modelfields import PhoneNumberField


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

    phone_number = PhoneNumberField(blank=True, null=True)
    access_agreement_signed_date = models.DateTimeField(blank=True, null=True)
    upgrade_request = models.DateTimeField(blank=True, null=True)


class EmailAddress(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='emailaddress_user')
    email = models.EmailField(
        'email address',
        unique=True,
        validators=[
            EmailValidator()
        ],
        error_messages={
            'unique': 'A user with that email address already exists.',
        }
    )
    is_verified = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Email Address'
        verbose_name_plural = 'Email Addresses'

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class ExpiringToken(Token):
    expiration = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Expiring Token'
