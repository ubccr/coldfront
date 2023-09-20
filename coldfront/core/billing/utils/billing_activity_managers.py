from abc import ABC
from abc import abstractmethod

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.billing.models import BillingActivity
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.user.models import UserProfile


class BillingActivityManager(ABC):
    """An interface for getting and setting the BillingActivity for a
    particular database entity."""

    entity_type = None
    container_type = None

    @abstractmethod
    def __init__(self, entity):
        """Validate the input's type and get the container that stores
        its BillingActivity, if any."""
        self._entity = entity
        assert isinstance(self._entity, self.entity_type)
        self._container = self._get_container()

    @property
    def billing_activity(self):
        """Return the BillingActivity object stored in the container, or
        None."""
        if self._container is None:
            self._container = self._get_container()
        if isinstance(self._container, self.container_type):
            # Refreshing sets the container to None if the container object has
            # been deleted.
            self._refresh_container()
        if isinstance(self._container, self.container_type):
            return self._deserialize_billing_activity()
        return None

    @billing_activity.setter
    def billing_activity(self, billing_activity):
        """Store the BillingActivity in the container, creating the
        container if needed."""
        assert isinstance(billing_activity, BillingActivity)
        value = self._serialize_billing_activity(billing_activity)
        if isinstance(self._container, self.container_type):
            # Refreshing sets the container to None if the container object has
            # been deleted.
            self._refresh_container()
        if isinstance(self._container, self.container_type):
            self._update_container_with_value(value)
        else:
            self._create_container_with_value(value)

    @property
    @abstractmethod
    def entity_str(self):
        pass

    @abstractmethod
    def _create_container_with_value(self, value):
        """Create the container to store the given value, and set the
        _container attribute to it."""
        pass

    @abstractmethod
    def _deserialize_billing_activity(self):
        """Return the BillingActivity object stored in the container."""
        pass

    @abstractmethod
    def _get_container(self):
        """Return the database object (container) related to the entity
        that stores the BillingActivity on its behalf, or None."""
        pass

    def _get_container_or_none(self, **container_kwargs):
        """Return the database object with the expected container type
        that matches the given filtering keyword arguments, or None."""
        try:
            return self.container_type.objects.get(**container_kwargs)
        except self.container_type.DoesNotExist:
            return None

    def _refresh_container(self):
        """Refresh the container from the database. If it no longer
        exists, set it to None. This method should be called before
        getting or updating a BillingActivity."""
        try:
            self._container.refresh_from_db()
        except ObjectDoesNotExist:
            self._container = None

    @abstractmethod
    def _serialize_billing_activity(self, billing_activity):
        """Return a serialized version of the given BillingActivity that
        is suitable for storage in the container."""
        pass

    @abstractmethod
    def _update_container_with_value(self, value):
        """Update the already-existent container so that it stores the
        given value."""
        pass


class ProjectBillingActivityManager(BillingActivityManager):
    """A class for getting and setting the BillingActivity for a
    Project."""

    entity_type = Project
    container_type = AllocationAttribute

    def __init__(self, project):
        self._allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Billing Activity')
        self._allocation = get_project_compute_allocation(project)
        super().__init__(project)

    @property
    def entity_str(self):
        return self._entity.name

    def _create_container_with_value(self, value):
        self._container = AllocationAttribute.objects.create(
            allocation_attribute_type=self._allocation_attribute_type,
            allocation=self._allocation,
            value=value)

    def _deserialize_billing_activity(self):
        return BillingActivity.objects.get(pk=int(self._container.value))

    def _get_container(self):
        return self._get_container_or_none(
            allocation_attribute_type=self._allocation_attribute_type,
            allocation=self._allocation)

    def _serialize_billing_activity(self, billing_activity):
        return str(billing_activity.pk)

    def _update_container_with_value(self, value):
        self._container.value = value
        self._container.save()


class ProjectUserBillingActivityManager(BillingActivityManager):
    """A class for getting and setting the BillingActivity for a
    ProjectUser."""

    entity_type = ProjectUser
    container_type = AllocationUserAttribute

    def __init__(self, project_user):
        self._allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Billing Activity')
        self._allocation = get_project_compute_allocation(project_user.project)
        self._allocation_user = AllocationUser.objects.get(
            allocation=self._allocation, user=project_user.user)
        super().__init__(project_user)

    @property
    def entity_str(self):
        return f'({self._entity.project.name}, {self._entity.user.username})'

    def _create_container_with_value(self, value):
        self._container = self.container_type.objects.create(
            allocation_attribute_type=self._allocation_attribute_type,
            allocation=self._allocation,
            allocation_user=self._allocation_user,
            value=value)

    def _deserialize_billing_activity(self):
        return BillingActivity.objects.get(pk=int(self._container.value))

    def _get_container(self):
        return self._get_container_or_none(
            allocation_attribute_type=self._allocation_attribute_type,
            allocation=self._allocation,
            allocation_user=self._allocation_user)

    def _serialize_billing_activity(self, billing_activity):
        return str(billing_activity.pk)

    def _update_container_with_value(self, value):
        self._container.value = value
        self._container.save()


class UserBillingActivityManager(BillingActivityManager):
    """A class for getting and setting the BillingActivity for a
    User."""

    entity_type = User
    container_type = UserProfile

    def __init__(self, user):
        super().__init__(user)

    @property
    def entity_str(self):
        return self._entity.username

    def _create_container_with_value(self, value):
        self._container = self.container_type.objects.create(
            user=self._entity,
            billing_activity=value)

    def _deserialize_billing_activity(self):
        return self._container.billing_activity

    def _get_container(self):
        return self._get_container_or_none(user=self._entity)

    def _serialize_billing_activity(self, billing_activity):
        return billing_activity

    def _update_container_with_value(self, value):
        self._container.billing_activity = value
        self._container.save()
