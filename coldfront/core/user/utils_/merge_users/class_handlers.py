import inspect

from abc import ABC
from abc import abstractmethod

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from flags.state import flag_enabled

from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils import higher_project_user_role


class ClassHandlerFactory(object):
    """A factory for returning a concrete instance of ClassHandler for a
    particular class."""

    def get_handler(self, klass, *args, **kwargs):
        """Return an instantiated handler for the given class with the
        given arguments and keyword arguments."""
        assert inspect.isclass(klass)
        return self._get_handler_class(klass)(*args, **kwargs)

    @staticmethod
    def _get_handler_class(klass):
        """Return the appropriate handler class for the given class. If
        none are applicable, raise a ValueError."""
        handler_class_name = f'{klass.__name__}Handler'
        try:
            return globals()[handler_class_name]
        except KeyError:
            raise ValueError(f'No handler for class {klass.__name__}.')


class ClassHandler(ABC):
    """A class that handles transferring data from a source object of a
    particular class, and which belongs to a source user, to a
    destination user, when merging User accounts."""

    @abstractmethod
    def __init__(self, src_user, dst_user, src_obj, reporting_strategies=None):
        self._src_user = src_user
        self._dst_user = dst_user
        self._src_obj = src_obj
        # A corresponding object may or may not exist for the destination User.
        # Attempt to retrieve it in each concrete child class.
        self._dst_obj = None

        self._class_name = self._src_obj.__class__.__name__

        # Report messages using each of the given strategies.
        self._reporting_strategies = []
        if isinstance(reporting_strategies, list):
            for strategy in reporting_strategies:
                self._reporting_strategies.append(strategy)

    def run(self):
        """Transfer the source object from the source user to the
        destination user."""
        with transaction.atomic():
            if self._dst_obj:
                self._set_falsy_attrs()
            self._run_special_handling()
            if self._dst_obj:
                self._dst_obj.save()

    def _get_settable_if_falsy_attrs(self):
        """Return a list of attributes that, if falsy in the
        destination, should be updated to the value of the corresponding
        attribute in the source object."""
        return []

    def _handle_associated_object(self, transferred=False):
        """An object B may be associated with a User through a different
        object A. When A is deleted, B may be deleted with it. When A is
        transferred, B is transferred with it. Record that this has
        occurred."""
        if not transferred:
            # The object was deleted.
            message = (
                f'{self._class_name}({self._src_obj.pk}): indirectly deleted')
            self._report_success_message(message)
        else:
            # The object was transferred to the destination user.
            self._record_update(
                self._src_obj.pk, 'user (indirectly associated)',
                self._src_user, self._dst_user)

    def _report_success_message(self, message):
        """Record a success message with the given text to each of the
        reporting strategies."""
        for strategy in self._reporting_strategies:
            strategy.success(message)

    def _record_update(self, pk, attr_name, pre_value, post_value):
        """Record that the object of this class and with the given
        primary key had its attribute with the given name updated from
        pre_value to post_value."""
        message = (
            f'{self._class_name}({pk}).{attr_name}: {pre_value} --> '
            f'{post_value}')
        self._report_success_message(message)

    def _run_special_handling(self):
        """Run handling specific to a particular class, implemented by
        each child class."""
        raise NotImplementedError

    def _set_attr_if_falsy(self, attr_name):
        """If the attribute with the given name is falsy in the
        destination object but not in the source object, update the
        former's value to the latter's."""
        assert hasattr(self._src_obj, attr_name)
        assert hasattr(self._dst_obj, attr_name)
        src_attr = getattr(self._src_obj, attr_name)
        dst_attr = getattr(self._dst_obj, attr_name)
        if src_attr and not dst_attr:
            setattr(self._dst_obj, attr_name, src_attr)
            self._record_update(self._dst_obj.pk, attr_name, dst_attr, src_attr)

    def _set_falsy_attrs(self):
        """TODO"""
        for attr_name in self._get_settable_if_falsy_attrs():
            self._set_attr_if_falsy(attr_name)
        self._dst_obj.save()

    def _transfer_src_obj_to_dst_user(self, attr_name='user'):
        """TODO"""
        setattr(self._src_obj, attr_name, self._dst_user)
        self._src_obj.save()
        self._record_update(
            self._src_obj.pk, attr_name, self._src_user, self._dst_user)


class UserProfileHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dst_obj = self._dst_user.userprofile

    def _get_settable_if_falsy_attrs(self):
        return [
            'is_pi',
            # Only the destination user should have a cluster UID.
            # 'cluster_uid',
            'phone_number',
            'access_agreement_signed_date',
            'billing_activity',
        ]

    def _run_special_handling(self):
        if flag_enabled('LRC_ONLY'):
            # TODO: Refactor shared logic between these methods.
            self._set_host_user()
            self._set_billing_activity()

    def _set_billing_activity(self):
        attr_name = 'billing_activity'
        src_activity = self._src_obj.billing_activity
        dst_activity = self._dst_obj.billing_activity
        if src_activity and dst_activity and src_activity != dst_activity:
            src_full_id = src_activity.full_id()
            dst_full_id = dst_activity.full_id()
            prompt = (
                f'{self._class_name}({self._dst_obj.pk}).{attr_name}: Conflict '
                f'requiring manual resolution. Type 1 or 2 to keep the '
                f'corresponding value.\n'
                f'1 - {src_full_id} (Source)\n'
                f'2 - {dst_full_id} (Destination)\n')
            choice = input(prompt)
            if choice == '1':
                self._dst_obj.billing_activity = src_activity
                self._record_update(
                    self._dst_obj.pk, attr_name, dst_full_id, src_full_id)
            elif choice == '2':
                pass
            else:
                raise ValueError('Invalid choice.')
        else:
            self._set_attr_if_falsy(attr_name)

    def _set_host_user(self):
        attr_name = 'host_user'
        src_host = self._src_obj.host_user
        dst_host = self._dst_obj.host_user
        if src_host and dst_host and src_host != dst_host:
            src_user_str = (
                f'{src_host.username} ({src_host.pk}, {src_host.first_name} '
                f'{src_host.last_name})')
            dst_user_str = (
                f'{dst_host.username} ({dst_host.pk}, {dst_host.first_name} '
                f'{dst_host.last_name})')
            prompt = (
                f'{self._class_name}({self._dst_obj.pk}).{attr_name}: Conflict '
                f'requiring manual resolution. Type 1 or 2 to keep the '
                f'corresponding value.\n'
                f'1 - {src_user_str} (Source)\n'
                f'2 - {dst_user_str} (Destination)\n')
            choice = input(prompt)
            if choice == '1':
                self._dst_obj.host_user = src_host
                self._record_update(
                    self._dst_obj.pk, attr_name, dst_host, src_host)
            elif choice == '2':
                pass
            else:
                raise ValueError('Invalid choice.')
        else:
            self._set_attr_if_falsy(attr_name)


class SocialAccountHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        self._transfer_src_obj_to_dst_user()


class EmailAddressHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        self._src_obj.primary = False
        self._transfer_src_obj_to_dst_user()


class AllocationUserHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self._dst_obj = AllocationUser.objects.get(
                allocation=self._src_obj.allocation, user=self._dst_user)
        except ObjectDoesNotExist:
            self._dst_obj = None

    def _run_special_handling(self):
        allocation = self._src_obj.allocation

        # TODO: Note that only compute Allocations are handled for now.

        assert allocation.resources.count() == 1
        resource = allocation.resources.first()
        assert resource.name.endswith(' Compute')

        if self._dst_obj:
            status_updated = self._update_status()
            if status_updated:
                self._dst_obj.save()
        else:
            self._transfer_src_obj_to_dst_user()

    def _update_status(self):
        """Update the status of the destination if it is not "Active"
        but the source's is. Return whether an update occurred."""
        active_allocation_user_status = \
            AllocationUserStatusChoice.objects.get(name='Active')
        dst_obj_status = self._dst_obj.status
        if (dst_obj_status != active_allocation_user_status and
                self._src_obj.status == active_allocation_user_status):
            self._dst_obj.status = self._src_obj.status
            self._record_update(
                self._dst_obj.pk, 'status', dst_obj_status.name,
                'Active')
            return True
        return False


class AllocationUserAttributeHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        transferred = self._src_obj.allocation_user.user == self._dst_user
        self._handle_associated_object(transferred=transferred)


class AllocationUserAttributeUsageHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        transferred = (
            self._src_obj.allocation_user_attribute.allocation_user.user ==
            self._dst_user)
        self._handle_associated_object(transferred=transferred)


class ClusterAccessRequestHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        transferred = self._src_obj.allocation_user.user == self._dst_user
        self._handle_associated_object(transferred=transferred)


class ProjectUserHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self._dst_obj = ProjectUser.objects.get(
                project=self._src_obj.project, user=self._dst_user)
        except ObjectDoesNotExist:
            self._dst_obj = None

    def _run_special_handling(self):
        if self._dst_obj:
            role_updated = self._update_role()
            status_updated = self._update_status()
            if role_updated or status_updated:
                self._dst_obj.save()
        else:
            self._transfer_src_obj_to_dst_user()

        # TODO: Run the runner?

    def _update_role(self):
        """Update the role of the destination if the source's is higher.
        Return whether an update occurred."""
        dst_obj_role = self._dst_obj.role
        self._dst_obj.role = higher_project_user_role(
            dst_obj_role, self._src_obj.role)
        if self._dst_obj.role != dst_obj_role:
            self._record_update(
                self._dst_obj.pk, 'role', dst_obj_role.name,
                self._dst_obj.role.name)
            return True
        return False

    def _update_status(self):
        """Update the status of the destination if it is not "Active"
        but the source's is. Return whether an update occurred."""
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        dst_obj_status = self._dst_obj.status
        if (self._dst_obj.status != active_project_user_status and
                self._src_obj.status == active_project_user_status):
            self._dst_obj.status = self._src_obj.status
            self._record_update(
                self._dst_obj.pk, 'status', dst_obj_status.name,
                'Active')
            return True
        return False


class ProjectUserJoinRequestHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        transferred = self._src_obj.project_user.user == self._dst_user
        self._handle_associated_object(transferred=transferred)


class SavioProjectAllocationRequestHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        if self._src_obj.requester == self._src_user:
            self._transfer_src_obj_to_dst_user(attr_name='requester')
        if self._src_obj.pi == self._src_user:
            self._transfer_src_obj_to_dst_user(attr_name='pi')
