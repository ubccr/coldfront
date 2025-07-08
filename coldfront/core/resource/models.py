# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

import coldfront.core.attribute_expansion as attribute_expansion


class AttributeType(TimeStampedModel):
    """An attribute type indicates the data type of the attribute. Examples include Date, Float, Int, Text, and Yes/No.

    Attributes:
        name (str): name of attribute data type
    """

    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = [
            "name",
        ]


class ResourceType(TimeStampedModel):
    """A resource type class links a resource and its value.

    Attributes:
        name (str): name of resource type
        description (str): description of resource type
    """

    class Meta:
        ordering = [
            "name",
        ]

    class ResourceTypeManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=255)
    history = HistoricalRecords()
    objects = ResourceTypeManager()

    @property
    def active_count(self):
        """
        Returns:
            int: the number of active resources of that type
        """

        return ResourceAttribute.objects.filter(resource__resource_type__name=self.name, value="Active").count()

    @property
    def inactive_count(self):
        """
        Returns:
            int: the number of inactive resources of that type
        """

        return ResourceAttribute.objects.filter(resource__resource_type__name=self.name, value="Inactive").count()

    def __str__(self):
        return self.name

    def natural_key(self):
        return [self.name]


class ResourceAttributeType(TimeStampedModel):
    """A resource attribute type indicates the type of the attribute. Examples include slurm_specs and slurm_cluster.

    Attributes:
        attribute_type (AttributeType): indicates the AttributeType of the attribute
        name (str): name of resource attribute type
        is_required (bool): indicates whether or not the attribute is required
        is_value_unique (bool): indicates whether or not the value is unique

    Note: the is_unique_per_resource field is rarely used, hence documentation does not exist.
    """

    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    is_required = models.BooleanField(default=False)
    is_unique_per_resource = models.BooleanField(default=False)
    is_value_unique = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

    class Meta:
        ordering = [
            "name",
        ]


class Resource(TimeStampedModel):
    """A resource is something a center maintains and provides access to for the community. Examples include Budgetstorage, Server, and Software License.

    Attributes:
        parent_resource (Resource): used for the Cluster Partition resource type as these partitions fall under a main cluster
        resource_type (ResourceType): the type of resource (Cluster, Storage, etc.)
        name (str): name of resource
        description (str): description of what the resource does and is used for
        is_available (bool): indicates whether or not the resource is available for users to request an allocation for
        is_public (bool):  indicates whether or not users can see the resource
        requires_payment (bool): indicates whether or not users have to pay to use this resource
        allowed_groups (Group): uses the Django Group model to allow certain user groups to request the resource
        allowed_users (User): links Django Users that are allowed to request the resource to the resource
    """

    class Meta:
        ordering = [
            "name",
        ]

    class ResourceManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    parent_resource = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True)
    resource_type = models.ForeignKey(ResourceType, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField()
    is_available = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    is_allocatable = models.BooleanField(default=True)
    requires_payment = models.BooleanField(default=False)
    allowed_groups = models.ManyToManyField(Group, blank=True)
    allowed_users = models.ManyToManyField(User, blank=True)
    linked_resources = models.ManyToManyField("self", blank=True)
    history = HistoricalRecords()
    objects = ResourceManager()

    def get_missing_resource_attributes(self, required=False):
        """
        Params:
            required (bool): indicates whether or not to get only the missing resource attributes that are required (if True, get only required missing attributes; else, get required and non-required missing attributes)

        Returns:
            list[ResourceAttribute]: a list of resource attributes that do not already exist for this resource
        """

        if required:
            resource_attributes = ResourceAttributeType.objects.filter(resource_type=self.resource_type, required=True)
        else:
            resource_attributes = ResourceAttributeType.objects.filter(resource_type=self.resource_type)

        missing_resource_attributes = []

        for attribute in resource_attributes:
            if not ResourceAttribute.objects.filter(resource=self, resource_attribute_type=attribute).exists():
                missing_resource_attributes.append(attribute)
        return missing_resource_attributes

    @property
    def status(self):
        """
        Returns:
            str: the status of the resource
        """

        return ResourceAttribute.objects.get(resource=self, resource_attribute_type__attribute="Status").value

    def get_attribute(self, name, expand=True, typed=True, extra_allocations=[]):
        """
        Params:
            name (str): name of the resource attribute type
            expand (bool): indicates whether or not to return the expanded value with attributes/parameters for attributes with a base type of 'Attribute Expanded Text'
            typed (bool): indicates whether or not to convert the attribute value to an int/ float/ str based on the base AttributeType name
            extra_allocations (list[Allocation]): allocations which are available to reference in the attribute list in addition to those associated with this ResourceAttribute

        Returns:
            str: the value of the first attribute found for this resource with the specified name
        """

        attr = self.resourceattribute_set.filter(resource_attribute_type__name=name).first()
        if attr:
            if expand:
                return attr.expanded_value(typed=typed, extra_allocations=extra_allocations)
            else:
                if typed:
                    return attr.typed_value()
                else:
                    return attr.value
        return None

    def get_attribute_list(self, name, expand=True, typed=True, extra_allocations=[]):
        """
        Params:
            name (str): name of the resource
            expand (bool): indicates whether or not to return the expanded value with attributes/parameters for attributes with a base type of 'Attribute Expanded Text'
            typed (bool): indicates whether or not to convert the attribute value to an int/ float/ str based on the base AttributeType name
            extra_allocations (list[Allocation]): allocations which are available to reference in the attribute list in addition to those associated with this ResourceAttribute

        Returns:
            list: the list of values of the attributes found with specified name
        """

        attr = self.resourceattribute_set.filter(resource_attribute_type__name=name).all()
        if expand:
            return [a.expanded_value(extra_allocations=extra_allocations, typed=typed) for a in attr]
        else:
            if typed:
                return [a.typed_value() for a in attr]
            else:
                return [a.value for a in attr]

    def get_ondemand_status(self):
        """
        Returns:
            str: If the resource has OnDemand status or not
        """

        ondemand = self.resourceattribute_set.filter(resource_attribute_type__name="OnDemand").first()
        if ondemand:
            return ondemand.value
        return None

    def __str__(self):
        return "%s (%s)" % (self.name, self.resource_type.name)

    def natural_key(self):
        return [self.name]


class ResourceAttribute(TimeStampedModel):
    """A resource attribute class links a resource attribute type and a resource.

    Attributes:
        resource_attribute_type (ResourceAttributeType): resource attribute type to link
        resource (Resource): resource to link
        value (str): value of the resource attribute
    """

    resource_attribute_type = models.ForeignKey(ResourceAttributeType, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    value = models.TextField()
    history = HistoricalRecords()

    def clean(self):
        """Validates the resource and raises errors if the resource is invalid."""
        expected_value_type = self.resource_attribute_type.attribute_type.name.strip()

        if expected_value_type == "Int" and not self.value.isdigit():
            raise ValidationError('Invalid Value "%s". Value must be an integer.' % (self.value))
        elif expected_value_type == "Active/Inactive" and self.value not in ["Active", "Inactive"]:
            raise ValidationError('Invalid Value "%s". Allowed inputs are "Active" or "Inactive".' % (self.value))
        elif expected_value_type == "Public/Private" and self.value not in ["Public", "Private"]:
            raise ValidationError('Invalid Value "%s". Allowed inputs are "Public" or "Private".' % (self.value))
        elif expected_value_type == "Date":
            try:
                datetime.strptime(self.value.strip(), "%m/%d/%Y")
            except ValueError:
                raise ValidationError('Invalid Value "%s". Date must be in format MM/DD/YYYY' % (self.value))

    def __str__(self):
        return "%s: %s (%s)" % (self.resource_attribute_type, self.value, self.resource)

    def typed_value(self):
        """
        Returns:
            int, float, str: the value of the attribute with proper type and is used for computing expanded_value() (coerced into int or float for attributes with Int or Float types; if it fails or the attribute is of any other type, it is coerced into a str)
        """

        raw_value = self.value
        atype_name = self.resource_attribute_type.attribute_type.name
        return attribute_expansion.convert_type(value=raw_value, type_name=atype_name)

    def expanded_value(self, typed=True, extra_allocations=[]):
        """
        Params:
            typed (bool): indicates whether or not to convert the attribute value to an int/ float/ str based on the base AttributeType name (unrecognized values not converted, so will return str)
            extra_allocations (list[Allocation]): allocations which are available to reference in the attribute list in addition to those associated with this ResourceAttribute

        Returns:
            int, float, str: the value of the attribute after attribute expansion

        For attributes with attribute type of 'Attribute Expanded Text' we look for an attribute with same name suffixed with '_attriblist' (this should be ResourceAttribute of the Resource associated with the attribute). If the attriblist attribute is found, we use it to generate a dictionary to use to expand the attribute value, and the expanded value is returned.

        If the expansion fails, or if no attriblist attribute is found, or if the attribute type is not 'Attribute Expanded Text', we just return the raw value.
        """

        raw_value = self.value
        if typed:
            # Try to convert to python type as per AttributeType
            raw_value = self.typed_value()

        if not attribute_expansion.is_expandable_type(self.resource_attribute_type.attribute_type):
            # We are not an expandable type, return raw value
            return raw_value

        allocs = extra_allocations
        resources = [self.resource]
        attrib_name = self.resource_attribute_type.name

        attriblist = attribute_expansion.get_attriblist_str(
            attribute_name=attrib_name, resources=resources, allocations=allocs
        )

        if not attriblist:
            # We do not have an attriblist, return raw value
            return raw_value

        expanded = attribute_expansion.expand_attribute(
            raw_value=raw_value,
            attribute_name=attrib_name,
            attriblist_string=attriblist,
            resources=resources,
            allocations=allocs,
        )
        return expanded

    class Meta:
        unique_together = ("resource_attribute_type", "resource")
