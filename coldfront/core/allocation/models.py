"""allocation models"""
import datetime
import logging
from ast import literal_eval
from enum import Enum

from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.utils.html import mark_safe
from django.utils.module_loading import import_string
from django.contrib.auth import get_user_model
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.config.env import ENV
from coldfront.core import attribute_expansion
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import import_from_settings
from coldfront.core.project.models import Project, ProjectPermission, ProjectUser


if ENV.bool('PLUGIN_IFX', default=False):
    from coldfront.core.utils.fasrc import get_resource_rate


logger = logging.getLogger(__name__)

ALLOCATION_ATTRIBUTE_VIEW_LIST = import_from_settings(
    'ALLOCATION_ATTRIBUTE_VIEW_LIST', []
)
ALLOCATION_FUNCS_ON_EXPIRE = import_from_settings('ALLOCATION_FUNCS_ON_EXPIRE', [])
ALLOCATION_RESOURCE_ORDERING = import_from_settings(
    'ALLOCATION_RESOURCE_ORDERING', ['-is_allocatable', 'resource_type', 'name']
)

class AllocationPermission(Enum):
    """ A project permission stores the user and manager fields of a project. """

    USER = 'USER'
    MANAGER = 'MANAGER'


class AllocationStatusChoice(TimeStampedModel):
    """ A project status choice indicates the status of the project. Examples include Active, Archived, and New.

    Attributes:
        name (str): name of project status choice
    """
    class Meta:
        ordering = ['name', ]

    class AllocationStatusChoiceManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=64)
    description = models.CharField(max_length=128, blank=True, null=True)
    objects = AllocationStatusChoiceManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


class Allocation(TimeStampedModel):
    """ An allocation provides users access to a resource.

    Attributes:
        project (Project): links the project the allocation falls under
        resources (Resource): links resources that this allocation allocates
        status (AllocationStatusChoice): represents the status of the allocation
        quantity (int): indicates the quantity of the resource for the allocation, if applicable
        start_date (Date): indicates the start date of the allocation
        end_date (Date): indicates the end/ expiry date of the allocation
        justification (str): text input from the user containing the justification for why the resource is being allocated
        description (str): description of the allocation
        is_locked (bool): indicates whether or not the allocation is locked
        is_changeable (bool): indicates whether or not the allocation is changeable
    """

    class Meta:
        ordering = ['project', ]

        permissions = (
            ('can_view_all_allocations', 'Can view all allocations'),
            ('can_review_allocation_requests', 'Can review allocation requests'),
            ('can_manage_invoice', 'Can manage invoice'),
        )

    project = models.ForeignKey(Project, on_delete=models.CASCADE,)
    resources = models.ManyToManyField(Resource)
    status = models.ForeignKey(
        AllocationStatusChoice, on_delete=models.CASCADE, verbose_name='Status'
    )
    quantity = models.IntegerField(default=1)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    justification = models.TextField()
    description = models.CharField(max_length=512, blank=True, null=True)
    is_locked = models.BooleanField(default=False)
    is_changeable = models.BooleanField(default=False)
    history = HistoricalRecords()

    def clean(self):
        """ Validates the allocation and raises errors if the allocation is invalid. """

        if self.status.name == 'Expired':
        #     if not self.end_date:
        #         raise ValidationError('You have to set the end date.')

            if self.end_date and self.end_date > datetime.datetime.now().date():
                raise ValidationError(
                    'End date cannot be greater than today.')

            if self.end_date and self.start_date > self.end_date:
                raise ValidationError(
                    'End date cannot be greater than start date.')

        elif self.status.name == 'Active':
            if not self.start_date:
                raise ValidationError('You have to set the start date.')


    def save(self, *args, **kwargs):
        """ Saves the project. """

        if self.pk:
            old_obj = Allocation.objects.get(pk=self.pk)
            if old_obj.status.name != self.status.name and self.status.name == 'Expired':
                for func_string in ALLOCATION_FUNCS_ON_EXPIRE:
                    func_to_run = import_string(func_string)
                    func_to_run(self.pk)

        super().save(*args, **kwargs)

    @property
    def offer_letter_code(self):
        return self.get_attribute('Offer Letter Code')

    @property
    def requires_payment(self):
        requires_payment = self.get_attribute('Requires Payment')
        if requires_payment == None:
            return self.get_parent_resource.requires_payment
        return requires_payment

    def get_slurm_spec_value(self, name):
        slurm_spec_value = None
        slurm_specs = self.get_attribute('slurm_specs')
        if slurm_specs is not None:
            for slurm_spec in self.get_attribute('slurm_specs').split(','):
                if name in slurm_spec:
                    slurm_spec_value = slurm_spec.replace(f'{name}=', '')
            return slurm_spec_value
        return ""

    @property
    def rawshares(self):
        return self.get_slurm_spec_value('RawShares')

    @property
    def fairshare(self):
        return self.get_slurm_spec_value('FairShare')

    @property
    def normshares(self):
        return self.get_slurm_spec_value('NormShares')

    @property
    def effectvusage(self):
        return self.get_attribute('EffectvUsage')

    @property
    def rawusage(self):
        return self.get_slurm_spec_value('RawUsage')

    @property
    def expense_code(self):
        return self.get_attribute('Expense Code')

    @property
    def heavy_io(self):
        return self.get_attribute('Heavy IO')

    @property
    def mounted(self):
        return self.get_attribute('Mounted')

    @property
    def external_sharing(self):
        return self.get_attribute('External Sharing')

    @property
    def high_security(self):
        return self.get_attribute('High Security')

    @property
    def dua(self):
        return self.get_attribute('DUA')

    def _return_size_attr_name(self, s_type='display'):
        parent_resource = self.get_parent_resource
        if not parent_resource:
            return None
        if 'Cluster' in parent_resource.resource_type.name:
            size_attr_name = 'Core Usage (Hours)'
        elif 'Storage' in parent_resource.resource_type.name:
            if s_type == 'exact':
                size_attr_name = 'Quota_In_Bytes'
            elif s_type=='display':
                size_attr_name = 'Storage Quota (TB)'
        else:
            return None
        return size_attr_name

    @property
    def size(self):
        size_attr_name = self._return_size_attr_name()
        if not size_attr_name:
            return None
        try:
            return float(self.get_attribute(size_attr_name))
        except ObjectDoesNotExist:
            if self.size_exact:
                if 'TB' in self.get_parent_resource.quantity_label:
                    divisor = 1099511627776
                    size = self.size_exact/divisor
                    if 'nesetape' in self.get_parent_resource.name:
                        size = round(size, -1)
                    return size
            return None
        except TypeError:
            return None

    @property
    def usage(self):
        size_attr_name = self._return_size_attr_name()
        if not size_attr_name:
            return None
        try:
            return float(self.allocationattribute_set.get(
                allocation_attribute_type__name=size_attr_name
            ).allocationattributeusage.value)
        except ObjectDoesNotExist:
            if self.usage_exact:
                if 'TB' in self.get_parent_resource.quantity_label:
                    divisor = 1099511627776
                    return self.usage_exact/divisor
            return None
        except TypeError:
            return None

    @property
    def size_exact(self):
        size_attr_name = self._return_size_attr_name(s_type='exact')
        if not size_attr_name:
            return None
        try:
            return self.get_attribute(size_attr_name, typed=True)
        except ObjectDoesNotExist:
            return None

    @property
    def usage_exact(self):
        size_attr_name = self._return_size_attr_name(s_type='exact')
        if not size_attr_name:
            return None
        try:
            return float(self.allocationattribute_set.get(
                allocation_attribute_type__name=size_attr_name
            ).allocationattributeusage.value)
        except ObjectDoesNotExist:
            return None

    @property
    def path(self):
        subdir_attribute = AllocationAttributeType.objects.get(name='Subdirectory')
        attr_filter = (
            Q(allocation_id=self.id) & Q(allocation_attribute_type_id=subdir_attribute.pk)
        )
        if AllocationAttribute.objects.filter(attr_filter):
            return AllocationAttribute.objects.get(attr_filter).value
        return ''

    @property
    def cost(self):
        try:
            price = float(get_resource_rate(self.resources.first().name))
        except AttributeError:
            return None
        except TypeError:
            return None
        except ObjectDoesNotExist:
            return None
        size_attr_name = self._return_size_attr_name()
        if not size_attr_name:
            return None
        size = self.allocationattribute_set.filter(
                    allocation_attribute_type__name=size_attr_name)
        size_value = None if not size else size.first().value
        return 0 if not size_value else price * float(size_value)

    @property
    def expires_in(self):
        """
        Returns:
            int: the number of days until the allocation expires
        """
        if self.end_date:
            return (self.end_date - datetime.date.today()).days
        return None

    @property
    def get_information(self, public_only=True):
        """
        Returns:
            str: the allocation's attribute type, usage out of total value, and usage out of total value as a percentage
        """
        html_string = ''
        if public_only:
            allocationattribute_set = self.allocationattribute_set.filter(
                allocation_attribute_type__is_private=False)
        else:
            allocationattribute_set = self.allocationattribute_set.all()
        for attribute in allocationattribute_set:
            if attribute.allocation_attribute_type.name in ALLOCATION_ATTRIBUTE_VIEW_LIST:
                html_string += '%s: %s <br>' % (
                    attribute.allocation_attribute_type.name, attribute.value)

            if hasattr(attribute, 'allocationattributeusage'):
                try:
                    # # set measurement using attribute.value
                    # quota, measurement = determine_size_fmt(attribute.allocation_attribute_type.name)

                    # usage = convert_size_fmt(num, measurement)
                    percent = round(float(attribute.allocationattributeusage.value) /
                                    float(attribute.value) * 10000) / 100
                except ValueError:
                    percent = 'Invalid Value'
                    logger.error("Allocation attribute '%s' for allocation id %s is not an int but has a usage",
                                 attribute.allocation_attribute_type.name, self.pk)
                except ZeroDivisionError:
                    percent = 100
                    logger.error("Allocation attribute '%s' for allocation id %s == 0 but has a usage",
                                 attribute.allocation_attribute_type.name, self.pk)

                string = '{}: {}/{} ({} %) <br>'.format(
                    attribute.allocation_attribute_type.name,
                    # usage,
                    round(attribute.allocationattributeusage.value, 2),
                    # quota,
                    attribute.value,
                    percent
                )
                html_string += string

        return mark_safe(html_string)

    @property
    def get_resources_as_string(self):
        """
        Returns:
            str: the resources for the allocation
        """

        return ', '.join([ele.name for ele in self.resources.all().order_by(
            *ALLOCATION_RESOURCE_ORDERING)])

    @property
    def get_resources_as_list(self):
        """
        Returns:
            list[Resource]: the resources for the allocation
        """

        return list(self.resources.all().order_by('-is_allocatable'))

    @property
    def get_parent_resource(self):
        """
        Returns:
            Resource: the parent resource for the allocation
        """
        if self.resources.count() == 0:
            return None
        if self.resources.count() == 1:
            return self.resources.first()
        parent = self.resources.order_by(*ALLOCATION_RESOURCE_ORDERING).first()
        if parent:
            return parent
        # Fallback
        return self.resources.first()

    @property
    def get_cluster(self):
        try:
            return self.resources.get(resource_type__name='Cluster')
        except Resource.DoesNotExist:
            logger.error(f'No cluster resource found for partition {self.project}')
            return None

    @property
    def is_cluster_allocation(self):
        cluster_found = False
        for resource in self.get_resources_as_list:
            if 'Cluster' in resource.resource_type.name:
                cluster_found = True
        return cluster_found

    @property
    def get_non_project_users(self):
        if 'Cluster' not in self.get_parent_resource.resource_type.name:
            return []
        project_user_list = [project_user.user for project_user in self.project.projectuser_set.filter(status__name='Active')]
        return self.allocationuser_set.filter(status__name='Active').exclude(user__in=project_user_list)

    def get_attribute(self, name, expand=True, typed=True, extra_allocations=[]):
        """
        Params:
            name (str): name of the allocation attribute type
            expand (bool): indicates whether or not to return the expanded value with attributes/parameters for attributes with a base type of 'Attribute Expanded Text'
            typed (bool): indicates whether or not to convert the attribute value to an int/ float/ str based on the base AttributeType name
            extra_allocations (list[Allocation]): allocations which are available to reference in the attribute list in addition to those associated with this AllocationAttribute

        Returns:
            str: the value of the first attribute found for this allocation with the specified name
        """

        attr = self.allocationattribute_set.filter(
            allocation_attribute_type__name=name).first()
        if attr:
            if expand:
                return attr.expanded_value(
                    extra_allocations=extra_allocations, typed=typed)
            if typed:
                return attr.typed_value()
            return attr.value
        return None

    def get_full_attribute(self, name):
        attr = self.allocationattribute_set.filter(
            allocation_attribute_type__name=name).first()
        if attr:
            return attr
        return None

    def set_usage(self, name, value):
        """
        Params:
            name (str): allocation attribute type whose usage to set
            value (float): value to set usage to
        """

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
        """
        Params:
            name (str): name of the allocation
            expand (bool): indicates whether or not to return the expanded value with attributes/parameters for attributes with a base type of 'Attribute Expanded Text'
            typed (bool): indicates whether or not to convert the attribute value to an int/ float/ str based on the base AttributeType name
            extra_allocations (list[Allocation]): allocations which are available to reference in the attribute list in addition to those associated with this AllocationAttribute

        Returns:
            list: the list of values of the attributes found with specified name
        """

        attr = self.allocationattribute_set.filter(
            allocation_attribute_type__name=name).all()
        if expand:
            return [a.expanded_value(typed=typed,
                extra_allocations=extra_allocations) for a in attr]
        if typed:
            return [a.typed_value() for a in attr]
        return [a.value for a in attr]

    def update_slurm_spec_value(self, key, value):
        try:
            slurm_spec_attribute = self.get_full_attribute('slurm_specs')
            for slurm_spec in self.get_attribute('slurm_specs').split(','):
                if key in slurm_spec:
                    old_slurm_spec_value = slurm_spec.replace(f'{key}=', '')
                    slurm_spec_attribute.value = self.get_attribute('slurm_specs').replace(f'{key}={old_slurm_spec_value}', f'{key}={value}')
                    slurm_spec_attribute.save()
                    return True
            return f'Error updating Allocation Slurm Spec value {key}={value} for {self.user.username} at {self.allocation}: Cant find key={key}'
        except Exception as e:
            error_message = f'Error updating Allocation Slurm Spec value {key}={value} for {self.user.username} at {self.allocation} : {str(e)}'
            logger.exception(error_message)
            return error_message

    def get_attribute_set(self, user):
        """
        Params:
            user (User): user for whom to return attributes

        Returns:
            list[AllocationAttribute]: returns the set of attributes the user is allowed to see (if superuser, then all allocation attributes; else, only non-private ones)
        """

        if user.is_superuser:
            return self.allocationattribute_set.all().order_by('allocation_attribute_type__name')

        return self.allocationattribute_set.filter(allocation_attribute_type__is_private=False).order_by('allocation_attribute_type__name')

    def user_permissions(self, user):
        """
        Params:
            user (User): user for whom to return permissions

        Returns:
            list[AllocationPermission]: list of user permissions for the allocation
        """

        if user.is_superuser:
            return list(AllocationPermission)

        project_perms = self.project.user_permissions(user)

        if ProjectPermission.DATA_MANAGER in project_perms:
            return [AllocationPermission.USER, AllocationPermission.MANAGER]

        managed_resources = [
            resource for resource in self.resources.all() if user in resource.allowed_users.all()]

        if managed_resources:
            return [AllocationPermission.USER, AllocationPermission.MANAGER]

        if self.project.projectuser_set.filter(user=user, status__name='Active').exists():
            return [AllocationPermission.USER]
        if self.allocationuser_set.filter(user=user, status__name__in=['Active', 'New']).exists():
            return [AllocationPermission.USER]

        return []

    def has_perm(self, user, perm):
        """
        Params:
            user (User): user to check permissions for
            perm (AllocationPermission): permission to check for in user's list

        Returns:
            bool: whether or not the user has the specified permission
        """

        perms = self.user_permissions(user)
        return perm in perms

    def user_can_manage_allocation(self, user):
        return self.has_perm(user, AllocationPermission.MANAGER)


    def __str__(self):
        tmp = self.get_parent_resource
        if tmp is None:
            return '%s' % (self.project.pi)
        return '%s (%s)' % (self.get_parent_resource.name, self.project.pi)


class AllocationAdminNote(TimeStampedModel):
    """ An allocation admin note is a note that an admin makes on an allocation.

    Attributes:
        allocation (Allocation): links the allocation to the note
        author (User): represents the User class of the admin who authored the note
        note (str): text input from the user containing the note
    """

    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    note = models.TextField()

    def __str__(self):
        return self.note


class AllocationUserNote(TimeStampedModel):
    """ An allocation user note is a note that an user makes on an allocation.

    Attributes:
        allocation (Allocation): links the allocation to the note
        author (User): represents the User class of the user who authored the note
        is_private (bool): indicates whether or not the note is private
        note (str): text input from the user containing the note
    """

    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_private = models.BooleanField(default=True)
    note = models.TextField()

    def __str__(self):
        return self.note


class AttributeType(TimeStampedModel):
    """ An attribute type indicates the data type of the attribute. Examples include Date, Float, Int, Text, and Yes/No.

    Attributes:
        name (str): name of attribute data type
    """
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class AllocationAttributeType(TimeStampedModel):
    """ An allocation attribute type indicates the type of the attribute. Examples include Cloud Account Name and Core Usage (Hours).

    Attributes:
        attribute_type (AttributeType): indicates the data type of the attribute
        name (str): name of allocation attribute type
        has_usage (bool): indicates whether or not the attribute type has usage
        is_required (bool): indicates whether or not the attribute is required
        is_unique (bool): indicates whether or not the value is unique
        is_private (bool): indicates whether or not the attribute type is private
        is_changeable (bool): indicates whether or not the attribute type is changeable
    """

    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    has_usage = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    is_private = models.BooleanField(default=True)
    is_changeable = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return '%s' % (self.name)

    class Meta:
        ordering = ['name', ]


class AllocationAttribute(TimeStampedModel):
    """ An allocation attribute class links an allocation attribute type and an allocation.

    Attributes:
        allocation_attribute_type (AllocationAttributeType): attribute type to link
        allocation (Allocation): allocation to link
        value (str): value of the allocation attribute
    """
    allocation_attribute_type = models.ForeignKey(
        AllocationAttributeType, on_delete=models.CASCADE)
    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    value = models.CharField(max_length=128)
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        """ Saves the allocation attribute. """

        super().save(*args, **kwargs)
        if self.allocation_attribute_type.has_usage and not AllocationAttributeUsage.objects.filter(allocation_attribute=self).exists():
            AllocationAttributeUsage.objects.create(
                allocation_attribute=self)

    def clean(self):
        """ Validates the allocation attribute and raises errors if the allocation attribute is invalid. """

        if self.allocation_attribute_type.is_unique and self.allocation.allocationattribute_set.filter(allocation_attribute_type=self.allocation_attribute_type).exclude(id=self.pk).exists():
            raise ValidationError(f"'{self.allocation_attribute_type}' attribute already exists for this allocation.")

        expected_value_type = self.allocation_attribute_type.attribute_type.name.strip()
        error = None
        if expected_value_type in ['Float', 'Int']:
            try:
                literal_val = literal_eval(self.value)
            except SyntaxError as exc:
                error = 'Value must be entirely numeric. Please remove any non-numeric characters.'
                raise ValidationError(
                    f'Invalid Value "{self.value}" for "{self.allocation_attribute_type.name}". {error}'
                )
            except ValueError as exc:
                error = 'Value must be numeric. Please enter a numeric value.'
                raise ValidationError(
                    f'Invalid Value "{self.value}" for "{self.allocation_attribute_type.name}". {error}'
                )
            if str(self.value) in ['True', 'False']:
                error = 'Value must be numeric. Please enter a numeric value.'
            elif expected_value_type == 'Float' and not isinstance(literal_val, (float,int)):
                error = 'Value must be a float.'
            elif expected_value_type == 'Int' and not isinstance(literal_val, int):
                error = 'Value must be an integer.'
        elif expected_value_type == "Yes/No" and self.value not in ["Yes", "No"]:
            error = 'Allowed inputs are "Yes" or "No".'
        elif expected_value_type == "Date":
            try:
                datetime.datetime.strptime(self.value.strip(), '%Y-%m-%d')
            except ValueError:
                error = 'Date must be in format YYYY-MM-DD'
        if error:
            raise ValidationError(
                f'Invalid Value "{self.value}" for "{self.allocation_attribute_type.name}". {error}'
            )

    def __str__(self):
        return str(self.allocation_attribute_type.name)

    def typed_value(self):
        """
        Returns:
            int, float, str: the value of the attribute with proper type and is used for computing expanded_value() (coerced into int or float for attributes with Int or Float types; if it fails or the attribute is of any other type, it is coerced into a str)
        """

        raw_value = self.value
        atype_name = self.allocation_attribute_type.attribute_type.name
        return attribute_expansion.convert_type(
            value=raw_value, type_name=atype_name)

    def expanded_value(self, extra_allocations=[], typed=True):
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
    """ Allocation attribute usage indicates the usage of an allocation attribute.

    Attributes:
        allocation_attribute (AllocationAttribute): links the usage to its allocation attribute
        value (float): usage value of the allocation attribute
    """

    allocation_attribute = models.OneToOneField(
        AllocationAttribute, on_delete=models.CASCADE, primary_key=True)
    value = models.FloatField(default=0)
    history = HistoricalRecords()

    def __str__(self):
        return '{}: {}'.format(self.allocation_attribute.allocation_attribute_type.name, self.value)


class AllocationUserStatusChoice(TimeStampedModel):
    """ An allocation user status choice indicates the status of an allocation user. Examples include Active, Error, and Removed.

    Attributes:
        name (str): name of the allocation user status choice
    """
    class Meta:
        ordering = ['name', ]

    class AllocationUserStatusChoiceManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=64)
    objects = AllocationUserStatusChoiceManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


class AllocationUser(TimeStampedModel):
    """ An allocation user represents a user on the allocation.

    Attributes:
        allocation (Allocation): links user to its allocation
        user (User): represents the User object of the allocation user
        status (ProjectUserStatus): links the project user status choice to the user
    """

    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE)
    # one user will have many AllocationUser
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.ForeignKey(AllocationUserStatusChoice, on_delete=models.CASCADE,
                               verbose_name='Allocation User Status')
    usage_bytes = models.BigIntegerField(blank=True, null=True)
    usage = models.FloatField(default = 0)
    unit = models.TextField(max_length=20, default='N/A Unit')

    history = HistoricalRecords()

    def __str__(self):
        if (self.allocation.resources.first() is None):
            return f'{self.user} (None)'
        return f'{self.user} ({self.allocation.resources.first().name})'

    class Meta:
        verbose_name_plural = 'Allocation User Status'
        unique_together = ('user', 'allocation')

    def get_attribute(self, name, typed=True):
        """
        Params:
            name (str): name of the allocation attribute type
            typed (bool): indicates whether or not to convert the attribute value to an int/ float/ str based on the base AttributeType name

        Returns:
            str: the value of the first attribute found for this allocation with the specified name
        """
        attr = self.allocationuserattribute_set.filter(
            allocationuser_attribute_type__name=name).first()
        if attr:
            if typed:
                return attr.typed_value()
            return attr.value
        return None

    def get_slurm_spec_value(self, name):
        slurm_spec_value = None
        slurm_specs = self.get_attribute('slurm_specs')
        if slurm_specs is not None:
            for slurm_spec in self.get_attribute('slurm_specs').split(','):
                if name in slurm_spec:
                    slurm_spec_value = slurm_spec.replace(f'{name}=', '')
            return slurm_spec_value
        return ""

    def update_slurm_spec_value(self, key, value):
        try:
            slurm_spec_attribute = self.allocationuserattribute_set.filter(allocationuser_attribute_type__name='slurm_specs').first()
            if slurm_spec_attribute is None: # AllocationUser does not have slurm_specs set up for this allocation (probably non project user)
                logger.warning('AllocationUser does not have slurm_specs set up for this allocation, creating default one (RawShares=0,NormShares=0,RawUsage=0,FairShare=0)')
                attribute_type = AllocationUserAttributeType.objects.get(name='slurm_specs')
                slurm_spec_attribute = AllocationUserAttribute(
                    allocationuser_attribute_type=attribute_type,
                    allocationuser=self,
                    value='RawShares=0,NormShares=0,RawUsage=0,FairShare=0'
                )
                slurm_spec_attribute.save()
            old_slurm_spec_value = self.get_slurm_spec_value(key)
            if old_slurm_spec_value in [""]:
                return f'Error updating AllocationUser Slurm Spec value {key}={value} for {self.user.username} at {self.allocation}: Cant find key={key}'
            slurm_spec_attribute.value = self.get_attribute('slurm_specs').replace(f'{key}={old_slurm_spec_value}', f'{key}={value}')
            slurm_spec_attribute.save()
            return True


        except Exception as e:
            error_message = f'Error updating AllocationUser Slurm Spec value {key}={value} for {self.user.username} at {self.allocation} : {str(e)}'
            logger.exception(error_message)
            return error_message

    @property
    def rawshares(self):
        return self.get_slurm_spec_value('RawShares')

    @property
    def fairshare(self):
        return self.get_slurm_spec_value('FairShare')

    @property
    def normshares(self):
        return self.get_slurm_spec_value('NormShares')

    @property
    def effectvusage(self):
        return self.get_slurm_spec_value('EffectvUsage')

    @property
    def rawusage(self):
        return self.get_slurm_spec_value('RawUsage')

    @property
    def user_usage(self):
        if self.unit == "CPU Hours":
            return self.usage
        return self.usage_bytes

    @property
    def allocation_usage(self):
        if self.unit == "CPU Hours":
            return self.allocation.size
        return self.allocation.usage_exact


class AllocationUserAttributeType(TimeStampedModel):
    """indicates the type of the allocationuser attribute. Examples: Fairshare, usage_in_bytes.

    Attributes:
        attribute_type (AttributeType): indicates the data type of the attribute
        name (str): name of allocation attribute type
        is_required (bool): indicates whether or not the attribute is required
        is_unique (bool): indicates whether or not the value is unique
        is_private (bool): indicates whether or not the attribute type is private
        is_changeable (bool): indicates whether or not the attribute type is changeable
    """

    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    is_private = models.BooleanField(default=True)
    is_changeable = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return '%s' % (self.name)

    class Meta:
        ordering = ['name', ]

class AllocationUserAttribute(TimeStampedModel):
    """links an allocation user attribute type and an allocation user.

    Attributes:
        allocationuser_attribute_type (AllocationAttributeType): attribute type to link
        allocationuser (Allocation): allocation to link
        value (str): value of the allocation attribute
    """
    allocationuser_attribute_type = models.ForeignKey(
        AllocationUserAttributeType, on_delete=models.CASCADE)
    allocationuser = models.ForeignKey(AllocationUser, on_delete=models.CASCADE)
    value = models.CharField(max_length=128)
    history = HistoricalRecords()

    def clean(self):
        """Validate allocationuser attribute, raise errors if the attribute is invalid."""

        if (
            self.allocation_attribute_type.is_unique
            and self.allocation.allocationattribute_set.filter(
                allocation_attribute_type=self.allocation_attribute_type
            ).exclude(id=self.pk).exists()
        ):
            raise ValidationError(
                f"'{self.allocation_attribute_type}' attribute already exists for this allocation."
            )

        expected_value_type = self.allocation_attribute_type.attribute_type.name.strip()
        error = None
        if expected_value_type == 'Float' and not isinstance(literal_eval(self.value), (float,int)):
            error = 'Value must be a float.'
        elif expected_value_type == 'Int' and not isinstance(literal_eval(self.value), int):
            error = 'Value must be an integer.'
        elif expected_value_type == 'Yes/No' and self.value not in ['Yes', 'No']:
            error = 'Allowed inputs are "Yes" or "No".'
        elif expected_value_type == 'Date':
            try:
                datetime.datetime.strptime(self.value.strip(), '%Y-%m-%d')
            except ValueError:
                error = 'Date must be in format YYYY-MM-DD'
        if error:
            raise ValidationError(
                'Invalid Value "%s" for "%s". %s' % (
                    self.value, self.allocation_attribute_type.name, error)
                )

    def __str__(self):
        return '%s %s' % (self.allocationuser_attribute_type.name, self.allocationuser)

    def typed_value(self):
        """
        Returns:
            int, float, str: the value of the attribute with proper type and
            is used for computing expanded_value() (coerced into int or float
            for attributes with Int or Float types; if it fails or the
            attribute is of any other type, it is coerced into a str)
        """
        raw_value = self.value
        atype_name = self.allocationuser_attribute_type.attribute_type.name
        return attribute_expansion.convert_type(
            value=raw_value, type_name=atype_name)


class AllocationAccount(TimeStampedModel):
    """ An allocation account
    #come back to

    Attributes:
        user (User): represents the User object of the project user
        name (str):
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class AllocationChangeStatusChoice(TimeStampedModel):
    """ An allocation change status choice represents statuses displayed when a user changes their allocation status (for allocations that have their is_changeable attribute set to True). Examples include Expired and Payment Pending.

    Attributes:
        name (str): status name
    """
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class AllocationChangeRequest(TimeStampedModel):
    """ An allocation change request represents a request from a PI or manager to change their allocation.

    Attributes:
        allocation (Allocation): represents the allocation to change
        status (AllocationStatusChoice): represents the allocation status of the changed allocation
        end_date_extension (int): represents the number of days to extend the allocation's end date
        justification (str): represents input from the user justifying why they want to change the allocation
        notes (str): represents notes for users changing allocations
    """

    allocation = models.ForeignKey(Allocation, on_delete=models.CASCADE,)
    status = models.ForeignKey(
        AllocationChangeStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    end_date_extension = models.IntegerField(blank=True, null=True)
    justification = models.TextField()
    notes = models.CharField(max_length=512, blank=True, null=True)
    history = HistoricalRecords()

    @property
    def get_parent_resource(self):
        """
        Returns:
            Resource: the parent resource for the allocation
        """

        if self.allocation.resources.count() == 1:
            return self.allocation.resources.first()
        return self.allocation.resources.filter(is_allocatable=True).first()

    def __str__(self):
        tmp = self.get_parent_resource
        if tmp is None:
            return '(%s)' % (self.allocation.project.pi)
        return '%s (%s)' % (self.get_parent_resource.name, self.allocation.project.pi)

class AllocationAttributeChangeRequest(TimeStampedModel):
    """ An allocation attribute change request represents a request from a PI/ manager to change their allocation attribute.

    Attributes:
        allocation_change_request (AllocationChangeRequest): links the change request from which this attribute change is derived
        allocation_attribute (AllocationAttribute): represents the allocation_attribute to change
        new_value (str): new value of allocation attribute
    """

    allocation_change_request = models.ForeignKey(AllocationChangeRequest, on_delete=models.CASCADE)
    allocation_attribute = models.ForeignKey(AllocationAttribute, on_delete=models.CASCADE)
    new_value = models.CharField(max_length=128)
    history = HistoricalRecords()

    def __str__(self):
        return '%s' % (self.allocation_attribute.allocation_attribute_type.name)
