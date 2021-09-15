from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator
from django.db import models
from django.core.exceptions import ValidationError
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    new_email_flag = models.BooleanField(blank=True, null=True)

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
    is_primary = models.BooleanField(default=False,
                                     help_text="Change is_primary status in list display.")

    class Meta:
        verbose_name = 'Email Address'
        verbose_name_plural = 'Email Addresses'

    def save(self, *args, **kwargs):
        self.email = self.email.lower()

        if self.new_email_flag or self.new_email_flag is None:
            old_primary_val = True
        else:
            # old primary val: if unsetting primary status, no error should pop
            old_primary_val = EmailAddress.objects.get(pk=self.pk).is_primary

        # checks if another primary email exists
        primary_emails_exist = EmailAddress.objects.filter(user=self.user).filter(is_primary=True).exists()

        # also checks if new is_primary is True. should mean that changing is_verified works
        if self.is_primary and not old_primary_val and primary_emails_exist:
            raise ValidationError('User already has a primary email address. Manually unset the primary '
                                  'email before setting a new primary email.')
        elif self.is_primary and not old_primary_val:
            # Set the User's email field if updating is_primary = True

            if not self.is_verified:
                raise ValidationError('Only verified emails may be set to primary.')

            self.user.email = self.email
            self.user.save()

        self.new_email_flag = False
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class ExpiringToken(Token):
    expiration = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Expiring Token'
