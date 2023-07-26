import inspect
import logging

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
    """A factory for returning a class that handles merging data from a
    source object into a destination object of a given class when
    merging User accounts."""

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
    """TODO"""

    @abstractmethod
    def __init__(self, src_user, dst_user, src_obj):
        """TODO"""
        self._src_user = src_user
        self._dst_user = dst_user
        self._src_obj = src_obj
        self._dst_obj = None

        self._logger = logging.getLogger(__name__)
        self._dry = False

    def dry_run(self):
        """TODO"""
        self._dry = True
        self.run()

    def run(self):
        """TODO"""
        with transaction.atomic():
            # TODO: Consider whether special handling may need to happen first.
            if self._dst_obj:
                self._set_falsy_attrs()
            self._run_special_handling()
            if self._dst_obj:
                self._dst_obj.save()

    def _get_settable_if_falsy_attrs(self):
        """TODO"""
        return []

    def _run_special_handling(self):
        """TODO"""
        raise NotImplementedError

    def _set_attr_if_falsy(self, attr_name):
        """TODO"""
        assert hasattr(self._src_obj, attr_name)
        assert hasattr(self._dst_obj, attr_name)

        src_attr = getattr(self._src_obj, attr_name)
        dst_attr = getattr(self._dst_obj, attr_name)

        if src_attr and not dst_attr:
            if self._dry:
                # TODO: Print.
                pass
            else:
                setattr(self._dst_obj, attr_name, src_attr)
                # TODO: Log.
                #  Only flush to the log at the end of the transaction, or
                #  Log that the transaction is being rolled back.
                #  Include a UUID in each log message to identify the merge.

    def _set_falsy_attrs(self):
        """TODO"""
        for attr_name in self._get_settable_if_falsy_attrs():
            self._set_attr_if_falsy(attr_name)
        self._dst_obj.save()

    def _transfer_src_obj_to_dst_user(self):
        """TODO"""
        if not self._dry:
            self._src_obj.user = self._dst_user
            self._src_obj.save()


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
        """TODO"""
        self._set_host_user()

    def _set_host_user(self):
        if flag_enabled('LRC_ONLY'):
            # TODO
            #  Deal with conflicts.
            #  Handle LBL users.
            self._set_attr_if_falsy('host_user')


class SocialAccountHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        """TODO"""
        self._transfer_src_obj_to_dst_user()


class EmailAddressHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        """TODO"""
        # TODO
        #  Consider allowing a new primary to be set.
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
        """TODO"""
        allocation = self._src_obj.allocation

        # TODO: Note that only compute Allocations are handled for now.

        assert allocation.resources.count() == 1
        resource = allocation.resources.first()
        assert resource.name.endswith(' Compute')

        if self._dst_obj:
            active_allocation_user_status = \
                AllocationUserStatusChoice.objects.get(name='Active')
            if (self._dst_obj.status != active_allocation_user_status and
                    self._dst_obj.status == active_allocation_user_status):
                self._dst_obj.status = self._src_obj.status
                self._dst_obj.save()
        else:
            self._src_obj.user = self._dst_user
            self._src_obj.save()


class AllocationUserAttributeHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        # TODO: This block is duplicated. Factor it out.
        try:
            self._src_obj.refresh_from_db()
        except ObjectDoesNotExist:
            # The object was deleted.
            # TODO: Log and write to output.
            return
        else:
            # The object was transferred to the destination user.
            # TODO: Log and write to output.
            return


class AllocationUserAttributeUsageHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        try:
            self._src_obj.refresh_from_db()
        except ObjectDoesNotExist:
            # The object was deleted.
            # TODO: Log and write to output.
            return
        else:
            # The object was transferred to the destination user.
            # TODO: Log and write to output.
            return


class ClusterAccessRequestHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        try:
            self._src_obj.refresh_from_db()
        except ObjectDoesNotExist:
            # The object was deleted.
            # TODO: Log and write to output.
            return
        else:
            # The object was transferred to the destination user.
            # TODO: Log and write to output.
            return


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
            self._dst_obj.role = higher_project_user_role(
                self._dst_obj.role, self._src_obj.role)

            active_project_user_status = ProjectUserStatusChoice.objects.get(
                name='Active')
            if (self._dst_obj.status != active_project_user_status and
                    self._src_obj.status == active_project_user_status):
                self._dst_obj.status = self._src_obj.status
                self._dst_obj.save()
        else:
            self._src_obj.user = self._dst_user
            self._src_obj.save()

        # TODO: Run the runner?


class ProjectUserJoinRequestHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        try:
            self._src_obj.refresh_from_db()
        except ObjectDoesNotExist:
            # The object was deleted.
            # TODO: Log and write to output.
            return
        else:
            # The object was transferred to the destination user.
            # TODO: Log and write to output.
            return


class SavioProjectAllocationRequestHandler(ClassHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _run_special_handling(self):
        if self._src_obj.requester == self._src_user:
            self._src_obj.requester = self._dst_user
        if self._src_obj.pi == self._src_user:
            self._src_obj.pi = self._dst_user
        self._src_obj.save()
