from coldfront.core.billing.models import BillingActivity
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from model_utils.models import TimeStampedModel
from phonenumber_field.modelfields import PhoneNumberField
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

    phone_number = PhoneNumberField(blank=True, null=True)
    access_agreement_signed_date = models.DateTimeField(blank=True, null=True)
    upgrade_request = models.DateTimeField(blank=True, null=True)

    billing_activity = models.ForeignKey(
        BillingActivity, blank=True, null=True, on_delete=models.SET_NULL)

    host_user = models.ForeignKey(
        User, related_name='host_user', blank=True, null=True, on_delete=models.SET_NULL)


class EmailAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
    is_primary = models.BooleanField(
        default=False, help_text='Change is_primary status in list display.')

    class Meta:
        verbose_name = 'Email Address'
        verbose_name_plural = 'Email Addresses'

    def save(self, *args, **kwargs):
        self.email = self.email.lower()

        if self.is_primary:
            try:
                was_primary = EmailAddress.objects.get(pk=self.pk).is_primary
            except EmailAddress.DoesNotExist:
                was_primary = False
            if not was_primary:
                # The address is going from not being primary to being primary.
                f = Q(user=self.user) & Q(is_primary=True) & ~Q(pk=self.pk)
                if EmailAddress.objects.filter(f).exists():
                    # Raise an error if a different address is already primary.
                    raise ValidationError(
                        'User already has a primary email address. Manually '
                        'unset the primary email before setting a new primary '
                        'email.')
                else:
                    # Non-verified addresses should not be set to primary.
                    if not self.is_verified:
                        raise ValidationError(
                            'Only verified emails may be set to primary.')
                    self.user.email = self.email
                    self.user.save()
            else:
                # The address was and is still primary; set the user's email
                # field in case it differs.
                self.user.email = self.email
                self.user.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class ExpiringToken(Token):
    expiration = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Expiring Token'


class IdentityLinkingRequestStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)


class IdentityLinkingRequest(TimeStampedModel):
    requester = models.ForeignKey(User, on_delete=models.CASCADE)
    request_time = models.DateTimeField(
        null=True, blank=True, default=timezone.now)
    completion_time = models.DateTimeField(null=True, blank=True)
    status = models.ForeignKey(
        IdentityLinkingRequestStatusChoice, on_delete=models.CASCADE)
