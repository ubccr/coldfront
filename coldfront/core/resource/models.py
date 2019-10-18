from datetime import datetime

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords


class AttributeType(TimeStampedModel):
    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class ResourceType(TimeStampedModel):
    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=255)
    history = HistoricalRecords()

    @property
    def active_count(self):
        return ResourceAttribute.objects.filter(
            resource__resource_type__name=self.name, value="Active").count()

    @property
    def inactive_count(self):
        return ResourceAttribute.objects.filter(
            resource__resource_type__name=self.name, value="Inactive").count()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class ResourceAttributeType(TimeStampedModel):
    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    is_required = models.BooleanField(default=False)
    is_unique_per_resource = models.BooleanField(default=False)
    is_value_unique = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class Resource(TimeStampedModel):
    parent_resource = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True)
    resource_type = models.ForeignKey(ResourceType, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField()
    is_available = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    is_allocatable = models.BooleanField(default=True)
    requires_payment = models.BooleanField(default=False)
    allowed_groups = models.ManyToManyField(Group, blank=True)
    allowed_users = models.ManyToManyField(User, blank=True)
    linked_resources = models.ManyToManyField('self', blank=True)
    history = HistoricalRecords()

    def get_missing_resource_attributes(self, required=False):
        """
        if required == True, get only the required missing attributes;
        otherwise, get required and non-required missing attributes
        """
        if required:
            resource_attributes = ResourceAttributeType.objects.filter(
                resource_type=self.resource_type, required=True)
        else:
            resource_attributes = ResourceAttributeType.objects.filter(
                resource_type=self.resource_type)

        missing_resource_attributes = []

        for attribute in resource_attributes:
            if not ResourceAttribute.objects.filter(resource=self, resource_attribute_type=attribute).exists():
                missing_resource_attributes.append(attribute)
        return missing_resource_attributes

    @property
    def status(self):
        return ResourceAttribute.objects.get(resource=self, resource_attribute_type__attribute="Status").value

    def get_attribute(self, name):
        attr = self.resourceattribute_set.filter(
            resource_attribute_type__name=name).first()
        if attr:
            return attr.value
        return None

    def get_attribute_list(self, name):
        attr = self.resourceattribute_set.filter(
            resource_attribute_type__name=name).all()
        return [a.value for a in attr]

    def __str__(self):
        return '%s (%s)' % (self.name, self.resource_type.name)

    class Meta:
        ordering = ['name', ]


class ResourceAttribute(TimeStampedModel):
    resource_attribute_type = models.ForeignKey(
        ResourceAttributeType, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    value = models.TextField()
    history = HistoricalRecords()

    def clean(self):

        expected_value_type = self.resource_attribute_type.attribute_type.name.strip()

        if expected_value_type == "Int" and not self.value.isdigit():
            raise ValidationError(
                'Invalid Value "%s". Value must be an integer.' % (self.value))
        elif expected_value_type == "Active/Inactive" and self.value not in ["Active", "Inactive"]:
            raise ValidationError(
                'Invalid Value "%s". Allowed inputs are "Active" or "Inactive".' % (self.value))
        elif expected_value_type == "Public/Private" and self.value not in ["Public", "Private"]:
            raise ValidationError(
                'Invalid Value "%s". Allowed inputs are "Public" or "Private".' % (self.value))
        elif expected_value_type == "Date":
            try:
                datetime.strptime(self.value.strip(), "%m/%d/%Y")
            except ValueError:
                raise ValidationError(
                    'Invalid Value "%s". Date must be in format MM/DD/YYYY' % (self.value))

    def __str__(self):
        return '%s: %s (%s)' % (self.resource_attribute_type, self.value, self.resource)

    class Meta:
        unique_together = ('resource_attribute_type', 'resource')
