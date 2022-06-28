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

    def is_one_per_pi(self):
        """Return whether a PI may have at most one of the allowance."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.FCA)
            allowance_names.append(BRCAllowances.ICA)
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

    def get_name(self):
        """Return the name of the underlying Resource."""
        return self._name

    def get_resource(self):
        """Return the underlying Resource."""
        return self._resource

    def requires_memorandum_of_understanding(self):
        """Return whether the allowance requires an MOU to be signed."""
        allowance_names = []
        if flag_enabled('BRC_ONLY'):
            allowance_names.append(BRCAllowances.ICA)
            allowance_names.append(BRCAllowances.RECHARGE)
        elif flag_enabled('LRC_ONLY'):
            allowance_names.append(LRCAllowances.RECHARGE)
        return self._name in allowance_names
