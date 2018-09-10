import datetime
import logging

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import mark_safe
from model_utils.models import TimeStampedModel

from core.djangoapps.project.models import Project
from core.djangoapps.resources.models import Resource
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)

class SubscriptionStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class Subscription(TimeStampedModel):
    """ Subscription to a system Resource. """
    project = models.ForeignKey(Project, on_delete=models.CASCADE,)
    resources = models.ManyToManyField(Resource)
    status = models.ForeignKey(SubscriptionStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    quantity = models.IntegerField(default=1)
    active_until = models.DateField(blank=True, null=True)
    justification = models.TextField()
    history = HistoricalRecords()

    class Meta:
        ordering = ['active_until']

        permissions = (
            ('can_view_all_subscriptions', 'Can see all subscriptions'),
            ('can_review_subscription_requests', 'Can review subscription requests'),
        )

    def clean(self):
        if self.status.name == 'Expired' and self.active_until > datetime.datetime.now().date():
            raise ValidationError(
                'You cannot set the status of this subscription to expired without changing the active until date.')

        elif self.status.name == 'Active' and self.active_until < datetime.datetime.now().date():
            raise ValidationError(
                'You cannot set the status of this subscription to active without changing the active until date.')

    @property
    def expires_in(self):
        return (self.active_until - datetime.date.today()).days

    @property
    def get_usage(self):
        html_string = ''
        for attribute in self.subscriptionattribute_set.all():

            if hasattr(attribute, 'subscriptionattributeusage'):
                try:
                    percent = round(float(attribute.subscriptionattributeusage.value) /
                                    float(attribute.value) * 10000) / 100
                except ValueError:
                    percent = 'Invalid Value'
                    logger.error("Subscription attribute '%s' is not an int but has a usage", attribute.subscription_attribute_type.name)

                string = '{}: {}/{} ({} %) <br>'.format(
                    attribute.subscription_attribute_type.name,
                    attribute.subscriptionattributeusage.value,
                    attribute.value,
                    percent
                )
                html_string += string

        return mark_safe(html_string)

    @property
    def get_resources_as_string(self):
        return ', '.join([ele.name for ele in self.resources.all().order_by('-is_subscribable')])

    @property
    def get_parent_resource(self):
        return self.resources.filter(is_subscribable=True).first()

    def __str__(self):
        return "%s (%s)" % (self.resources.first().name, self.project.pi)


class SubscriptionAdminComment(TimeStampedModel):
    """ SubscriptionAttributeType. """
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()

    def __str__(self):
        return self.comment


class SubscriptionUserMessage(TimeStampedModel):
    """ SubscriptionAttributeType. """
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return self.message


class AttributeType(TimeStampedModel):
    """ AttributeType. """
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class SubscriptionAttributeType(TimeStampedModel):
    """ SubscriptionAttributeType. """
    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    has_usage = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class SubscriptionAttribute(TimeStampedModel):
    """ SubscriptionAttribute. """
    subscription_attribute_type = models.ForeignKey(SubscriptionAttributeType, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    value = models.CharField(max_length=128)
    is_private = models.BooleanField(default=True)
    history = HistoricalRecords()

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
        return '%s' % (self.subscription_attribute_type.name)


class SubscriptionAttributeUsage(TimeStampedModel):
    """ SubscriptionAttributeUsage. """
    subscription_attribute = models.OneToOneField(SubscriptionAttribute, on_delete=models.CASCADE, primary_key=True)
    value = models.FloatField(default=0)
    history = HistoricalRecords()

    def __str__(self):
        return '{}: {}'.format(self.subscription_attribute.subscription_attribute_type.name, self.value)


class SubscriptionUserStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class SubscriptionUser(TimeStampedModel):
    """ SubscriptionUserStatus. """
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.ForeignKey(SubscriptionUserStatusChoice, on_delete=models.CASCADE,
                               verbose_name='Subscription User Status')
    history = HistoricalRecords()

    def __str__(self):
        return '%s (%s)' % (self.user, self.subscription.resources.first().name)

    class Meta:
        verbose_name_plural = 'Subscription User Status'
        unique_together = ('user', 'subscription')
