from flags.state import flag_enabled

from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances


class ComputingAllowance(object):
    """A wrapper class around a Resource representing a computing
    allowance, with helper methods."""

    def __init__(self, resource):
        assert isinstance(resource, Resource)
        self._resource = resource
        self._name = self._resource.name

    def are_service_units_prorated(self):
        """Return whether the allowance's service units should be
        prorated."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.FCA)
            allowance_names.append(BRCAllowances.PCA)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.PCA)
        return self._name in allowance_names

    def are_service_units_user_specified(self):
        """Return whether the allowance's service units are specified by
        the user."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.RECHARGE)
        return self._name in allowance_names

    def has_infinite_service_units(self):
        """Return whether the allowance has an effectively-infinite
        number of service units (i.e., there is no limit)."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.CO)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.LR)
            allowance_names.append(LRCAllowances.RECHARGE)
        return self._name in allowance_names

    def is_instructional(self):
        """Return whether the allowance is for a course."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.ICA)
        return self._name in allowance_names

    def is_one_per_pi(self):
        """Return whether a PI may have at most one of the allowance."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.FCA)
            allowance_names.append(BRCAllowances.PCA)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.PCA)
        return self._name in allowance_names

    def is_periodic(self):
        """Return whether the allowance is limited to a specific
        AllocationPeriod."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.FCA)
            allowance_names.append(BRCAllowances.ICA)
            allowance_names.append(BRCAllowances.PCA)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.PCA)
        return self._name in allowance_names

    def is_poolable(self):
        """Return whether the allowance may be pooled with another of
        the same type."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.FCA)
            allowance_names.append(BRCAllowances.PCA)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.PCA)
        return self._name in allowance_names

    def is_recharge(self):
        """Return whether the allowance is paid for."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.RECHARGE)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.RECHARGE)
        return self._name in allowance_names

    def is_renewable(self):
        """Return whether the allowance may theoretically be renewed."""
        return self.is_periodic()

    def is_renewal_supported(self):
        """Return whether there is support for renewing the
        allowance."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.FCA)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.PCA)
        return self._name in allowance_names

    def is_yearly(self):
        """Return whether the allowance conforms to the allowance
        year."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.FCA)
            allowance_names.append(BRCAllowances.PCA)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.PCA)
        return self._name in allowance_names

    def get_name(self):
        """Return the name of the underlying Resource."""
        return self._name

    def get_resource(self):
        """Return the underlying Resource."""
        return self._resource

    def requires_extra_information(self):
        """Return whether the allowance requires extra user-specified
        information."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.ICA)
            allowance_names.append(BRCAllowances.RECHARGE)
        return self._name in allowance_names

    def requires_memorandum_of_understanding(self):
        """Return whether the allowance requires an MOU to be signed."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.ICA)
            allowance_names.append(BRCAllowances.RECHARGE)
        return self._name in allowance_names
