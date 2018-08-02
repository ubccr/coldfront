import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import mark_safe
from model_utils.models import TimeStampedModel

from core.djangoapps.project.models import Project
from core.djangoapps.resources.models import Resource


class SubscriptionStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Subscription(TimeStampedModel):
    """ Subscription to a system Resource. """
    project = models.ForeignKey(Project, on_delete=models.CASCADE,)
    resources = models.ManyToManyField(Resource)
    status = models.ForeignKey(SubscriptionStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    quantity = models.IntegerField(default=1)
    active_until = models.DateField(blank=True, null=True)
    justification = models.TextField()

    class Meta:
        ordering = ['active_until']

        permissions = (
            ('can_view_all_subscriptions', 'Can see all subscriptions'),
            ('can_review_pending_subscriptions', 'Can review pending subscriptions'),
        )

    def save(self, *args, **kwargs):
        if self.active_until < datetime.datetime.now().date():
            self.status = SubscriptionStatusChoice.objects.get(name='Expired')
        elif self.active_until > datetime.datetime.now().date():
            self.status = SubscriptionStatusChoice.objects.get(name='Active')

        super().save(*args, **kwargs)

    @property
    def expires_in(self):
        return (self.active_until - datetime.date.today()).days

    @property
    def get_usage(self):
        html_string = ''
        for attribute in self.subscriptionattribute_set.all():
            if hasattr(attribute, 'subscriptionattributeusage'):
                percent = round(float(attribute.subscriptionattributeusage.value) /
                                float(attribute.value) * 10000) / 100
                string = '{}: {}/{} ({} %) <br>'.format(
                    attribute.subscription_attribute_type.name,
                    attribute.subscriptionattributeusage.value,
                    attribute.value,
                    percent
                )
                html_string += string

        return mark_safe(html_string)

    def __str__(self):
        return "%s (%s)" % (self.resources.first().name, self.project.pi)


class AttributeType(TimeStampedModel):
    """ AttributeType. """
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class SubscriptionAttributeType(TimeStampedModel):
    """ SubscriptionAttributeType. """
    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    has_usage = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class SubscriptionAttribute(TimeStampedModel):
    """ SubscriptionAttribute. """
    subscription_attribute_type = models.ForeignKey(SubscriptionAttributeType, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    value = models.CharField(max_length=128)
    is_private = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.subscription_attribute_type.has_usage and not SubscriptionAttributeUsage.objects.filter(subscription_attribute=self).exists():
            SubscriptionAttributeUsage.objects.create(subscription_attribute=self)

    def clean(self):
        expected_value_type = self.subscription_attribute_type.name.strip()
        if expected_value_type == "Int" and not isinstance(self.value, int):
            raise ValidationError('Invalid Value "%s". Value must be an integer.' % (self.value))
        elif expected_value_type == "Float" and not isinstance(self.value, float):
            raise ValidationError('Invalid Value "%s". Value must be a float.' % (self.value))
        elif expected_value_type == "Yes/No" and self.value not in ["Yes", "No"]:
            raise ValidationError('Invalid Value "%s". Allowed inputs are "Yes" or "No".' % (self.value))

    def __str__(self):
        return '%s: %s ' % (self.subscription_attribute_type.name, self.value)


class SubscriptionAttributeUsage(TimeStampedModel):
    """ SubscriptionAttributeUsage. """
    subscription_attribute = models.OneToOneField(SubscriptionAttribute, on_delete=models.CASCADE, primary_key=True)
    value = models.FloatField(default=0)

    def __str__(self):
        return '{}: {}'.format(self.subscription_attribute.subscription_attribute_type.name, self.value)


class SubscriptionUserStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class SubscriptionUser(TimeStampedModel):
    """ SubscriptionUserStatus. """
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.ForeignKey(SubscriptionUserStatusChoice, on_delete=models.CASCADE,
                               verbose_name='Subscription User Status')

    def __str__(self):
        return '%s (%s)' % (self.user, self.subscription.resources.first().name)

    class Meta:
        verbose_name_plural = 'Subscription User Status'
        unique_together = ('user', 'subscription')
