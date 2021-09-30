from datetime import datetime

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords
import coldfront.core.attribute_expansion as attribute_expansion

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

    def get_attribute(self, name, expand=True, typed=True, 
        extra_allocations=[]):
        """Return the value of the first attribute found with specified name

        This will return the value of the first attribute found for this
        resource with the specified name.

        If expand is True (the default), we will return the expanded_value()
        method of the attribute, which will expand attributes/parameters in
        the attribute value for attributes with a base type of 'Attribute
        Expanded Text'.  If the attribute is not of that type, or expand is
        false, returns the value attribute/data member (i.e. the raw, unexpanded
        value).

        If extra_allocations is given, it should be a list of Allocations, and
        when expand=True, the attributes of those Allocations (in addition to
        attributes of the Resources associated with this ResourceAttribute) are
        available for referencing in the attribute list.

        If typed is True (the default), we will attempt to convert the value
        returned to the appropriate python type (int/float/str) based on the
        base AttributeType name.
        """
        attr = self.resourceattribute_set.filter(
            resource_attribute_type__name=name).first()
        if attr:
            if expand:
                return attr.expanded_value(
                    typed=typed, extra_allocations=extra_allocations)
            else:
                if typed:
                    return attr.typed_value()
                else:
                    return attr.value
        return None

    def get_attribute_list(self, name, expand=True, typed=True,
        extra_allocations=[]):
        """Return a list of values of the attributes found with specified name

        This will return a list consisting of the values of the all attributes
        found for this resource with the specified name.

        If expand is True (the default), we will return the result of the
        expanded_value() method for each attribute, which will expand
        attributes/parameters in the attribute value for attributes with a base 
        type of 'Attribute Expanded Text'.  If the attribute is not of that 
        type, or expand is false, returns the value attribute/data member (i.e.
         the raw, unexpanded value).

        If extra_allocations is given, it should be a list of Allocations, and
        when expand=True, the attributes of those Allocations (in addition to
        attributes of the Resources associated with this ResourceAttribute) are
        available for referencing in the attribute list.

        If typed is True (the default), we will attempt to convert the value
        returned to the appropriate python type (int/float/str) based on the
        base AttributeType name.
        """
        attr = self.resourceattribute_set.filter(
            resource_attribute_type__name=name).all()
        if expand:
            return [a.expanded_value(extra_allocations=extra_allocations,
                typed=typed) for a in attr]
        else:
            if typed:
                return [a.typed_value() for a in attr]
            else:
                return [a.value for a in attr]

    def get_ondemand_status(self):
        ondemand = self.resourceattribute_set.filter(
            resource_attribute_type__name='OnDemand').first()
        if ondemand:
            return ondemand.value
        return None
            
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

    def typed_value(self):
        """Returns the value of the attribute, with proper type.

        For attributes with Int or Float types, we return the value of
        the attribute coerced into an Int or Float.  If the coercion
        fails, we log a warning and return the string.

        For all other attribute types, we return the value as a string.

        This is needed when computing values for expanded_value()
        """
        raw_value = self.value
        atype_name = self.resource_attribute_type.attribute_type.name
        return attribute_expansion.convert_type(
            value=raw_value, type_name=atype_name)

    def expanded_value(self, typed=True, extra_allocations=[]):
        """Returns the value of the attribute, after attribute expansion.

        For attributes with attribute type of  'Attribute Expanded Text' we
        look for an attribute with same name suffixed with '_attriblist' (this
        should be ResourceAttribute of the Resource associated with the
        attribute).
        If the attriblist attribute is found, we use
        it to generate a dictionary to use to expand the attribute value,
        and the expanded value is returned.  

        If extra_allocations is given, it should be a list of Allocations, and
        the attributes of these allocations will be available for referencing
        in the attriblist (in addition to attributes of the Resource associated
        with this ResourceAttribute).

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
            self.resource_attribute_type.attribute_type):
            # We are not an expandable type, return raw value
            return raw_value

        allocs = extra_allocations
        resources = [ self.resource ]
        attrib_name = self.resource_attribute_type.name

        attriblist = attribute_expansion.get_attriblist_str(
            attribute_name = attrib_name,
            resources = resources,
            allocations = allocs)

        if not attriblist:
            # We do not have an attriblist, return raw value
            return raw_value

        expanded = attribute_expansion.expand_attribute(
            raw_value = raw_value, 
            attribute_name = attrib_name,
            attriblist_string = attriblist,
            resources = resources,
            allocations = allocs)
        return expanded

    class Meta:
        unique_together = ('resource_attribute_type', 'resource')
