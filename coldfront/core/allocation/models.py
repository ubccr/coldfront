import datetime
import importlib
import logging
from ast import literal_eval

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import mark_safe
from django.utils.module_loading import import_string
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import import_from_settings
import coldfront.core.attribute_expansion as attribute_expansion

logger = logging.getLogger(__name__)

ALLOCATION_ATTRIBUTE_VIEW_LIST = import_from_settings(
    'ALLOCATION_ATTRIBUTE_VIEW_LIST', [])
ALLOCATION_FUNCS_ON_EXPIRE = import_from_settings(
    'ALLOCATION_FUNCS_ON_EXPIRE', [])
ALLOCATION_RESOURCE_ORDERING = import_from_settings(
    'ALLOCATION_RESOURCE_ORDERING',
    ['-is_allocatable', 'name'])


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
    is_changeable = models.BooleanField(default=False)
    history = HistoricalRecords()

    class Meta:
        ordering = ['end_date', ]

        permissions = (
            ('can_view_all_allocations', 'Can view all allocations'),
            ('can_review_allocation_requests',
             'Can review allocation requests'),
            ('can_manage_invoice', 'Can manage invoice'),
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
            if attribute.allocation_attribute_type.name in ALLOCATION_ATTRIBUTE_VIEW_LIST:
                html_string += '%s: %s <br>' % (
                    attribute.allocation_attribute_type.name, attribute.value)

            if hasattr(attribute, 'allocationattributeusage'):
                try:
                    percent = round(float(attribute.allocationattributeusage.value) /
                                    float(attribute.value) * 10000) / 100
                except ValueError:
                    percent = 'Invalid Value'
                    logger.error("Allocation attribute '%s' is not an int but has a usage",
                                 attribute.allocation_attribute_type.name)
                except ZeroDivisionError:
                    percent = 100
                    logger.error("Allocation attribute '%s' == 0 but has a usage",
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
        return ', '.join([ele.name for ele in self.resources.all().order_by(
            *ALLOCATION_RESOURCE_ORDERING)])

    @property
    def get_resources_as_list(self):
        return [ele for ele in self.resources.all().order_by('-is_allocatable')]

    @property
    def get_parent_resource(self):
        if self.resources.count() == 1:
            return self.resources.first()
        else:
            parent = self.resources.order_by(
                *ALLOCATION_RESOURCE_ORDERING).first()
            if parent:
                return parent
            # Fallback
            return self.resources.first()

    def get_attribute(self, name, expand=True, typed=True,
        extra_allocations=[]):
        """Return the value of the first attribute found with specified name

        This will return the value of the first attribute found for this
        allocation with the specified name.

        If expand is True (the default), we will return the expanded_value()
        method of the attribute, which will expand attributes/parameters in
        the attribute value for attributes with a base type of 'Attribute
        Expanded Text'.  If the attribute is not of that type, or expand is
        false, returns the value attribute/data member (i.e. the raw, unexpanded
        value).

        Extra_allocations is a list of Allocations which, if expand is True,
        will have their attributes available for referencing.

        If typed is True (the default), we will attempt to convert the value
        returned to the appropriate python type (int/float/str) based on the
        base AttributeType name.
        """
        attr = self.allocationattribute_set.filter(
            allocation_attribute_type__name=name).first()
        if attr:
            if expand:
                return attr.expanded_value(
                    extra_allocations=extra_allocations, typed=typed)
            else:
                if typed:
                    return attr.typed_value()
                else:
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

    def get_attribute_list(self, name, expand=True, typed=True,
        extra_allocations=[]):
        """Return a list of values of the attributes found with specified name

        This will return a list consisting of the values of the all attributes
        found for this allocation with the specified name.

        If expand is True (the default), we will return the result of the
        expanded_value() method for each attribute, which will expand 
        attributes/parameters in the attribute value for attributes with a base 
        type of 'Attribute Expanded Text'.  If the attribute is not of that 
        type, or expand is false, returns the value attribute/data member (i.e. 
        the raw, unexpanded value).

        Extra_allocations is a list of Allocations which, if expand is True,
        will have their attributes available for referencing.
        """
        attr = self.allocationattribute_set.filter(
            allocation_attribute_type__name=name).all()
        if expand:
            return [a.expanded_value(typed=typed,
                extra_allocations=extra_allocations) for a in attr]
        else:
            if typed:
                return [a.typed_value() for a in attr]
            else:
                return [a.value for a in attr]

    def __str__(self):
        return "%s (%s)" % (self.get_parent_resource.name, self.project.pi)


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
    is_changeable = models.BooleanField(default=False)
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

        if expected_value_type == "Int" and not isinstance(literal_eval(self.value), int):
            raise ValidationError(
                'Invalid Value "%s" for "%s". Value must be an integer.' % (self.value, self.allocation_attribute_type.name))
        elif expected_value_type == "Float" and not (isinstance(literal_eval(self.value), float) or isinstance(literal_eval(self.value), int)):
            raise ValidationError(
                'Invalid Value "%s" for "%s". Value must be a float.' % (self.value, self.allocation_attribute_type.name))
        elif expected_value_type == "Yes/No" and self.value not in ["Yes", "No"]:
            raise ValidationError(
                'Invalid Value "%s" for "%s". Allowed inputs are "Yes" or "No".' % (self.value, self.allocation_attribute_type.name))
        elif expected_value_type == "Date":
            try:
                datetime.datetime.strptime(self.value.strip(), "%Y-%m-%d")
            except ValueError:
                raise ValidationError(
                    'Invalid Value "%s" for "%s". Date must be in format YYYY-MM-DD' % (self.value, self.allocation_attribute_type.name))

    def __str__(self):
        return '%s' % (self.allocation_attribute_type.name)

    def typed_value(self):
        """Returns the value of the attribute, with proper type.

        For attributes with Int or Float types, we return the value of
        the attribute coerced into an Int or Float.  If the coercion
        fails, we log a warning and return the string.

        For all other attribute types, we return the value as a string.

        This is needed when computing values for expanded_value()
        """
        raw_value = self.value
        atype_name = self.allocation_attribute_type.attribute_type.name
        return attribute_expansion.convert_type(
            value=raw_value, type_name=atype_name)
                
    
    def expanded_value(self, extra_allocations=[], typed=True):
        """Returns the value of the attribute, after attribute expansion.

        For attributes with attribute type of  'Attribute Expanded Text' we
        look for an attribute with same name suffixed with '_attriblist' (this
        should be either an AllocationAttribute of the Allocation associated
        with this attribute  or a ResourceAttribute of a Resource of the 
        Allocation associated with this AllocationAttribute).  
        If the attriblist attribute is found, we use
        it to generate a dictionary to use to expand the attribute value,
        and the expanded value is returned.  
        If extra_allocations is given, it should be a list of Allocations and
        the attriblist can reference attributes for allocations in the
        extra_allocations list (as well as in the Allocation associated with
        this AllocationAttribute or Resources associated with that allocation)

        If typed is True (the default), we use typed to convert the returned
        value to the expected (int, float, str) python data type according to
        the AttributeType of the AllocationAttributeType (unrecognized values
        not converted, so will return str).

        If the expansion fails, or if no attriblist attribute is found, or if
        the attribute type is not 'Attribute Expanded Text', we just return
        the raw value.
        """
        raw_value = self.value
        if typed:
            # Try to convert to python type as per AttributeType
            raw_value = self.typed_value()

        if not attribute_expansion.is_expandable_type(
            self.allocation_attribute_type.attribute_type):
            # We are not an expandable type, return raw_value
            return raw_value

        allocs = [ self.allocation ] + extra_allocations
        resources = list(self.allocation.resources.all())
        attrib_name = self.allocation_attribute_type.name

        attriblist = attribute_expansion.get_attriblist_str(
            attribute_name = attrib_name,
            resources = resources,
            allocations = allocs)

        if not attriblist:
            # We do not have an attriblist, return raw_value
            return raw_value

        expanded = attribute_expansion.expand_attribute(
            raw_value = raw_value,
            attribute_name = attrib_name,
            attriblist_string = attriblist,
            resources = resources,
            allocations = allocs)
        return expanded

            

class AllocationAttributeUsage(TimeStampedModel):
    """ AllocationAttributeUsage. """
    allocation_attribute = models.OneToOneField(
        AllocationAttribute, on_delete=models.CASCADE, primary_key=True)
    value = models.FloatField(default=0)
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


class AllocationChangeStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class AllocationChangeRequest(TimeStampedModel):
    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE,)
    status = models.ForeignKey(
        AllocationChangeStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    end_date_extension = models.IntegerField(blank=True, null=True)
    justification = models.TextField()
    notes = models.CharField(max_length=512, blank=True, null=True)
    history = HistoricalRecords()

    @property
    def get_parent_resource(self):
        if self.allocation.resources.count() == 1:
            return self.allocation.resources.first()
        else:
            return self.allocation.resources.filter(is_allocatable=True).first()

    def __str__(self):
        return "%s (%s)" % (self.get_parent_resource.name, self.allocation.project.pi)


class AllocationAttributeChangeRequest(TimeStampedModel):
    allocation_change_request = models.ForeignKey(AllocationChangeRequest, on_delete=models.CASCADE)
    allocation_attribute = models.ForeignKey(AllocationAttribute, on_delete=models.CASCADE)
    new_value = models.CharField(max_length=128)
    history = HistoricalRecords()

    def __str__(self):
        return '%s' % (self.allocation_attribute.allocation_attribute_type.name)

