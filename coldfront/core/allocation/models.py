import datetime
import importlib
import logging
from ast import literal_eval
from collections import namedtuple
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.html import mark_safe
from django.utils.module_loading import import_string
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)


ALLOCATION_FUNCS_ON_EXPIRE = import_from_settings(
    'ALLOCATION_FUNCS_ON_EXPIRE', [])
SLURM_ACCOUNT_ATTRIBUTE_NAME = import_from_settings(
    'SLURM_ACCOUNT_ATTRIBUTE_NAME', 'slurm_account_name')


class AllocationStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class Allocation(TimeStampedModel):
    """ Allocation to a system Resource. """
    project = models.ForeignKey(Project, on_delete=models.CASCADE,)
    resources = models.ManyToManyField(Resource)
    status = models.ForeignKey(
        AllocationStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    quantity = models.IntegerField(default=1)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    justification = models.TextField()
    description = models.CharField(max_length=512, blank=True, null=True)
    is_locked = models.BooleanField(default=False)
    history = HistoricalRecords()

    class Meta:
        ordering = ['end_date', ]

        permissions = (
            ('can_view_all_allocations', 'Can view all allocations'),
            ('can_review_allocation_requests',
             'Can review allocation requests'),
            ('can_manage_invoice', 'Can manage invoice'),
            ('can_review_cluster_account_requests',
             'Can review cluster account requests'),
        )

    def clean(self):
        if self.status.name == 'Expired':
            if not self.end_date:
                raise ValidationError('You have to set the end date.')

            if self.end_date > datetime.datetime.now().date():
                raise ValidationError(
                    'End date cannot be greater than today.')

            if self.start_date > self.end_date:
                raise ValidationError(
                    'End date cannot be greater than start date.')

        elif self.status.name == 'Active':
            if not self.start_date:
                raise ValidationError('You have to set the start date.')

            if not self.end_date:
                raise ValidationError('You have to set the end date.')

            if self.start_date > self.end_date:
                raise ValidationError(
                    'Start date cannot be greater than the end date.')

    def save(self, *args, **kwargs):
        if self.pk:
            old_obj = Allocation.objects.get(pk=self.pk)
            if old_obj.status.name != self.status.name and self.status.name == 'Expired':
                for func_string in ALLOCATION_FUNCS_ON_EXPIRE:
                    func_to_run = import_string(func_string)
                    func_to_run(self.pk)

        super().save(*args, **kwargs)

    @property
    def expires_in(self):
        return (self.end_date - datetime.date.today()).days

    @property
    def get_information(self):
        html_string = ''
        for attribute in self.allocationattribute_set.all():

            if attribute.allocation_attribute_type.name in [SLURM_ACCOUNT_ATTRIBUTE_NAME, ]:
                html_string += '%s: %s <br>' % (
                    attribute.allocation_attribute_type.name, attribute.value)

            if hasattr(attribute, 'allocationattributeusage'):
                try:
                    percent = round(float(attribute.allocationattributeusage.value) /
                                    float(attribute.value) * 10000) / 100
                except ZeroDivisionError:
                    percent = 0
                except ValueError:
                    percent = 'Invalid Value'
                    logger.error("Allocation attribute '%s' is not an int but has a usage",
                                 attribute.allocation_attribute_type.name)

                string = '{}: {}/{} ({} %) <br>'.format(
                    attribute.allocation_attribute_type.name,
                    attribute.allocationattributeusage.value,
                    attribute.value,
                    percent
                )
                html_string += string

        return mark_safe(html_string)

    @property
    def get_resources_as_string(self):
        return ', '.join([ele.name for ele in self.resources.all().order_by('-is_allocatable')])

    @property
    def get_parent_resource(self):
        if self.resources.count() == 1:
            return self.resources.first()
        else:
            return self.resources.filter(is_allocatable=True).first()

    def get_attribute(self, name):
        attr = self.allocationattribute_set.filter(
            allocation_attribute_type__name=name).first()
        if attr:
            return attr.value
        return None

    def set_usage(self, name, value):
        attr = self.allocationattribute_set.filter(
            allocation_attribute_type__name=name).first()
        if not attr:
            return

        if not attr.allocation_attribute_type.has_usage:
            return

        if not AllocationAttributeUsage.objects.filter(allocation_attribute=attr).exists():
            usage = AllocationAttributeUsage.objects.create(
                allocation_attribute=attr)
        else:
            usage = attr.allocationattributeusage

        usage.value = value
        usage.save()

    def get_attribute_list(self, name):
        attr = self.allocationattribute_set.filter(
            allocation_attribute_type__name=name).all()
        return [a.value for a in attr]

    def __str__(self):
        return "%s (%s)" % (self.get_parent_resource.name, self.project.name)


class AllocationAdminNote(TimeStampedModel):
    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()

    def __str__(self):
        return self.note


class AllocationUserNote(TimeStampedModel):
    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_private = models.BooleanField(default=True)
    note = models.TextField()

    def __str__(self):
        return self.note


class AttributeType(TimeStampedModel):
    """ AttributeType. """
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class AllocationAttributeType(TimeStampedModel):
    """ AllocationAttributeType. """
    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    has_usage = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    is_private = models.BooleanField(default=True)
    history = HistoricalRecords()

    def __str__(self):
        return '%s (%s)' % (self.name, self.attribute_type.name)

    class Meta:
        ordering = ['name', ]


class AllocationAttribute(TimeStampedModel):
    """ AllocationAttribute. """
    allocation_attribute_type = models.ForeignKey(
        AllocationAttributeType, on_delete=models.CASCADE)
    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    value = models.CharField(max_length=128)
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.allocation_attribute_type.has_usage and not AllocationAttributeUsage.objects.filter(allocation_attribute=self).exists():
            AllocationAttributeUsage.objects.create(
                allocation_attribute=self)

    def clean(self):
        if self.allocation_attribute_type.is_unique and self.allocation.allocationattribute_set.filter(allocation_attribute_type=self.allocation_attribute_type).exists():
            raise ValidationError("'{}' attribute already exists for this allocation.".format(
                self.allocation_attribute_type))

        expected_value_type = self.allocation_attribute_type.attribute_type.name.strip()
        validate_allocation_attribute_value_type(
            expected_value_type, self.value)

    def __str__(self):
        return '%s' % (self.allocation_attribute_type.name)


class AllocationAttributeUsage(TimeStampedModel):
    """ AllocationAttributeUsage. """
    allocation_attribute = models.OneToOneField(
        AllocationAttribute, on_delete=models.CASCADE, primary_key=True)
    value = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_MAX_PLACES,
        default=settings.ALLOCATION_MIN,
        validators=[
            MinValueValidator(settings.ALLOCATION_MIN),
            MaxValueValidator(settings.ALLOCATION_MAX),
        ])
    history = HistoricalRecords()

    def __str__(self):
        return '{}: {}'.format(self.allocation_attribute.allocation_attribute_type.name, self.value)


class AllocationUserStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class AllocationUser(TimeStampedModel):
    """ AllocationUser. """
    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.ForeignKey(AllocationUserStatusChoice, on_delete=models.CASCADE,
                               verbose_name='Allocation User Status')
    history = HistoricalRecords()

    def __str__(self):
        return '%s (%s)' % (self.user, self.allocation.resources.first().name)

    class Meta:
        verbose_name_plural = 'Allocation User Status'
        unique_together = ('user', 'allocation')


class AllocationAccount(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class AllocationUserAttribute(TimeStampedModel):
    """ AllocationUserAttribute. """
    allocation_attribute_type = models.ForeignKey(
        AllocationAttributeType, on_delete=models.CASCADE)
    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    allocation_user = models.ForeignKey(
        AllocationUser, on_delete=models.CASCADE)
    value = models.CharField(max_length=128)
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if (self.allocation_attribute_type.has_usage and
                not AllocationUserAttributeUsage.objects.filter(
                    allocation_user_attribute=self).exists()):
            AllocationUserAttributeUsage.objects.create(
                allocation_user_attribute=self)

    def clean(self):
        if self.allocation_attribute_type.is_unique:
            kwargs = {
                "allocation_attribute_type": self.allocation_attribute_type,
            }
            if self.allocation.allocationuserattribute_set.filter(
                    **kwargs).exists():
                raise ValidationError(
                    ("'{}' attribute already exists for this "
                     "allocation.").format(self.allocation_attribute_type))

        expected_value_type = \
            self.allocation_attribute_type.attribute_type.name.strip()
        validate_allocation_attribute_value_type(
            expected_value_type, self.value)

    def __str__(self):
        return self.allocation_attribute_type.name


class AllocationUserAttributeUsage(TimeStampedModel):
    """ AllocationUserAttributeUsage. """
    allocation_user_attribute = models.OneToOneField(
        AllocationUserAttribute, on_delete=models.CASCADE, primary_key=True)
    value = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_MAX_PLACES,
        default=settings.ALLOCATION_MIN,
        validators=[
            MinValueValidator(settings.ALLOCATION_MIN),
            MaxValueValidator(settings.ALLOCATION_MAX),
        ])
    history = HistoricalRecords()

    def __str__(self):
        return '{}: {}'.format(
            self.allocation_user_attribute.allocation_attribute_type.name,
            self.value)


def validate_allocation_attribute_value_type(expected_value_type, value):
    """Raise a ValidationError if the given value does not conform to
    the requirements of the expected value type."""
    if (expected_value_type == 'Int' and
            not isinstance(literal_eval(value), int)):
        raise ValidationError(
            'Invalid Value "%s". Value must be an integer.' % value)
    elif (expected_value_type == 'Decimal' and
            not isinstance(literal_eval(value), (Decimal, int, str))):
        raise ValidationError(
            'Invalid Value "%s". Value must be a decimal.' % value)
    elif (expected_value_type == 'Float' and
          not isinstance(literal_eval(value), (float, int))):
        raise ValidationError(
            'Invalid Value "%s". Value must be a float.' % value)
    elif expected_value_type == 'Yes/No' and value not in ['Yes', 'No']:
        raise ValidationError(
            'Invalid Value "%s". Allowed inputs are "Yes" or "No".' % value)
    elif expected_value_type == 'Date':
        try:
            datetime.datetime.strptime(value.strip(), '%Y-%m-%d')
        except ValueError:
            raise ValidationError(
                ('Invalid Value "%s". Date must be in format '
                 'YYYY-MM-DD') % value)


class AllocationPeriod(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name


class AllocationRenewalRequestStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


def allocation_renewal_request_state_schema():
    """Return the schema for the AllocationRenewalRequest.state
    field."""
    return {
        'eligibility': {
            'status': 'Pending',
            'justification': '',
            'timestamp': '',
        },
        'other': {
            'justification': '',
            'timestamp': '',
        }
    }


class AllocationRenewalRequest(TimeStampedModel):
    requester = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='allocation_renewal_requester')
    pi = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='allocation_renewal_pi')
    allocation_period = models.ForeignKey(
        AllocationPeriod, on_delete=models.CASCADE)
    status = models.ForeignKey(
        AllocationRenewalRequestStatusChoice, on_delete=models.CASCADE)

    pre_project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name='allocation_renewal_pre_project')
    post_project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name='allocation_renewal_post_project')
    # Use quotation marks to avoid a circular import.
    new_project_request = models.OneToOneField(
        'project.SavioProjectAllocationRequest',
        null=True, blank=True, on_delete=models.CASCADE)

    num_service_units = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_MAX_PLACES,
        default=settings.ALLOCATION_MIN,
        validators=[
            MinValueValidator(settings.ALLOCATION_MIN),
            MaxValueValidator(settings.ALLOCATION_MAX),
        ])
    request_time = models.DateTimeField(
        null=True, blank=True, default=timezone.now)
    approval_time = models.DateTimeField(null=True, blank=True)
    completion_time = models.DateTimeField(null=True, blank=True)

    state = models.JSONField(default=allocation_renewal_request_state_schema)
    extra_fields = models.JSONField(default=dict)

    UNPOOLED_TO_UNPOOLED = 'unpooled_to_unpooled'
    UNPOOLED_TO_POOLED = 'unpooled_to_pooled'
    POOLED_TO_POOLED_SAME = 'pooled_to_pooled_same'
    POOLED_TO_POOLED_DIFFERENT = 'pooled_to_pooled_different'
    POOLED_TO_UNPOOLED_OLD = 'pooled_to_unpooled_old'
    POOLED_TO_UNPOOLED_NEW = 'pooled_to_unpooled_new'

    def get_pooling_preference_case(self):
        """Return a string denoting the pooling preference based on the
        contents of the request.

        Raise a ValueError if the case is unexpected.
        """
        pi = self.pi
        pre_project = self.pre_project
        post_project = self.post_project
        is_pooled_pre = pre_project and pre_project.is_pooled()
        is_pooled_post = post_project.is_pooled()
        if pre_project == post_project:
            if not is_pooled_pre:
                return self.UNPOOLED_TO_UNPOOLED
            else:
                return self.POOLED_TO_POOLED_SAME
        else:
            if self.new_project_request:
                return self.POOLED_TO_UNPOOLED_NEW
            else:
                if not is_pooled_pre:
                    if not is_pooled_post:
                        raise ValueError('Unexpected case.')
                    else:
                        return self.UNPOOLED_TO_POOLED
                else:
                    if pi in post_project.pis():
                        return self.POOLED_TO_UNPOOLED_OLD
                    else:
                        return self.POOLED_TO_POOLED_DIFFERENT

    def __str__(self):
        period = self.allocation_period.name
        pi = self.pi.username
        return f'Renewal Request ({period}, {pi})'


class AllocationAdditionRequestStatusChoice(TimeStampedModel):
    """A status that a AllocationAdditionRequest may have."""

    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


def allocation_addition_request_state_schema():
    """Return the schema for the AllocationAdditionRequest.state
    field."""
    return {
        'memorandum_signed': {
            'status': 'Pending',
            'timestamp': '',
        },
        'other': {
            'justification': '',
            'timestamp': '',
        }
    }


class AllocationAdditionRequest(TimeStampedModel):
    """A request to purchase additional Service Units for under eligible
    Project."""

    requester = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='allocation_addition_requester')
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name='allocation_addition_project')
    status = models.ForeignKey(
        AllocationAdditionRequestStatusChoice, on_delete=models.CASCADE)

    num_service_units = models.DecimalField(
        max_digits=settings.DECIMAL_MAX_DIGITS,
        decimal_places=settings.DECIMAL_MAX_PLACES,
        default=settings.ALLOCATION_MIN,
        validators=[
            MinValueValidator(settings.ALLOCATION_MIN),
            MaxValueValidator(settings.ALLOCATION_MAX),
        ])
    request_time = models.DateTimeField(
        null=True, blank=True, default=timezone.now)
    completion_time = models.DateTimeField(null=True, blank=True)

    state = models.JSONField(default=allocation_addition_request_state_schema)
    extra_fields = models.JSONField(default=dict)

    def __str__(self):
        project_name = self.project.name
        num_sus = self.num_service_units
        return f'Addition Request ({project_name}, {num_sus})'

    def denial_reason(self):
        """Return a namedtuple representing the reason why the request
        was denied, based on its 'state' field. Raise a ValueError if it
        doesn't have the 'Denied' status or if it has an unexpected
        state."""
        if self.status.name != 'Denied':
            raise ValueError(
                f'The request has unexpected status {self.status.name}.')
        state = self.state
        other = state['other']
        if other['timestamp']:
            category = 'Other'
            justification = other['justification']
            timestamp = other['timestamp']
        else:
            raise ValueError('The request has an unexpected state.')
        DenialReason = namedtuple(
            'DenialReason', 'category justification timestamp')
        return DenialReason(
            category=category, justification=justification,
            timestamp=timestamp)

    def latest_update_timestamp(self):
        """Return the latest timestamp stored in the request's 'state'
        field, or the empty string.

        The expected values are ISO 8601 strings, or the empty string,
        so taking the maximum should provide the correct output."""
        state = self.state
        max_timestamp = ''
        for field in state:
            max_timestamp = max(
                max_timestamp, state[field].get('timestamp', ''))
        return max_timestamp


class SecureDirAddUserRequestStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)
    # One of "Pending - Add", "Processing - Add", "Completed"

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class SecureDirAddUserRequest(TimeStampedModel):
    """A request to add a user to a secure directory"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE)
    allocation = models.ForeignKey(
        Allocation, on_delete=models.CASCADE)
    status = models.ForeignKey(
        SecureDirAddUserRequestStatusChoice, on_delete=models.CASCADE)