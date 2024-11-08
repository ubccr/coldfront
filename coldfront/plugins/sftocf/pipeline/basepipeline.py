from operator import itemgetter
import logging
from coldfront.core.allocation.models import Allocation,  AllocationAttributeType
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.local_utils import determine_size_fmt, id_present_missing_users, log_missing
from coldfront.plugins.sftocf.utils import AllocationQueryMatch, return_dict_of_groupings

logger = logging.getLogger(__name__)

PENDING_ACTIVE_ALLOCATION_STATUSES = import_from_settings(
    'PENDING_ACTIVE_ALLOCATION_STATUSES', ['Active', 'New', 'In Progress', 'On Hold'])
username_ignore_list = import_from_settings('USERNAME_IGNORE_LIST', [])


class UsageDataPipelineBase:
    """Base class for usage data pipeline classes."""

    def __init__(self, volume=None, sfserver=None):
        self.connection_obj = self.return_connection_obj(sfserver)
        if volume:
            self.volumes = [volume]
        else:
            resources = self.connection_obj.get_corresponding_coldfront_resources()
            self.volumes = [r.name.split('/')[0] for r in resources]

        self._allocations = None
        # self.collection_filter = self.set_collection_parameters()
        self.sf_user_data = self.collect_sf_user_data()
        self.sf_usage_data = self.collect_sf_usage_data()
        self._allocationquerymatches = None

    def return_connection_obj(self, sfserver):
        raise NotImplementedError

    def collect_sf_user_data(self):
        raise NotImplementedError

    def collect_sf_usage_data(self):
        raise NotImplementedError

    @property
    def allocations(self):
        if self._allocations:
            return self._allocations
        allocation_statuses = PENDING_ACTIVE_ALLOCATION_STATUSES+['Pending Deactivation']
        self._allocations = Allocation.objects.filter(
            status__name__in=allocation_statuses,
            resources__in=self.connection_obj.get_corresponding_coldfront_resources()
        )
        return self._allocations

    @property
    def allocationquerymatches(self):
        # limit allocations to those in the volumes collected
        if self._allocationquerymatches:
            return self._allocationquerymatches
        allocations = self.allocations.prefetch_related(
            'project','allocationattribute_set', 'allocationuser_set')
        allocation_list = [
            (a.get_parent_resource.name.split('/')[0], a.path) for a in allocations
        ]
        total_sort_key = itemgetter('path','volume')
        allocation_usage_grouped = return_dict_of_groupings(self.sf_usage_data, total_sort_key)
        missing_allocations = [
            (k,a) for k, a in allocation_usage_grouped if (a, k) not in allocation_list
        ]
        print("missing_allocations:", missing_allocations)
        logger.warning('starfish allocations missing in coldfront: %s', missing_allocations)

        user_usage = [user for user in self.sf_user_data if user['path'] is not None]
        user_sort_key = itemgetter('path','volume')
        user_usage_grouped = return_dict_of_groupings(user_usage, user_sort_key)

        missing_users = [u for k, u in user_usage_grouped.items() if k not in allocation_list]

        allocationquerymatch_objs = []
        for allocation in allocations:
            a = (str(allocation.path), str(allocation.get_parent_resource.name.split('/')[0]))
            total_usage_entries = allocation_usage_grouped.get(a, None)
            user_usage_entries = user_usage_grouped.get(a, [])
            allocationquerymatch_objs.append(
                AllocationQueryMatch(allocation, total_usage_entries, user_usage_entries)
            )
        self._allocationquerymatches = [a for a in allocationquerymatch_objs if a]
        return self._allocationquerymatches

    def clean_collected_data(self):
        """clean data
        - flag any users not present in coldfront
        """
        # make master list of all users missing from ifx; don't record them yet,
        # only do that if they appear for our allocations.
        user_usernames = {d['username'] for d in self.sf_user_data}
        user_models, missing_usernames = id_present_missing_users(user_usernames)
        missing_username_list = [d['username'] for d in missing_usernames]
        logger.debug('allocation_usage:\n%s', self.sf_usage_data)

        # identify and remove allocation users that are no longer in the AD group
        for obj in self.allocationquerymatches:
            missing_unames_metadata = [
                {
                    'username': d['username'],
                    'volume': d.get('volume', None),
                    'path': d.get('path', None),
                }
                for d in obj.users_in_list(missing_username_list)
                if d['username'] not in username_ignore_list
            ]
            log_missing('user', missing_unames_metadata)
            for i in obj.users_in_list(missing_username_list):
                obj.user_usage_entries.remove(i)
        return self.allocationquerymatches, user_models

    def update_coldfront_objects(self, user_models):
        """update coldfront objects"""
        allocation_attribute_types = AllocationAttributeType.objects.all()

        quota_b_attrtype = allocation_attribute_types.get(name='Quota_In_Bytes')
        quota_tb_attrtype = allocation_attribute_types.get(name='Storage Quota (TB)')
        # 3. iterate across allocations
        for obj in self.allocationquerymatches:
            logger.debug('updating allocation %s %s (path %s)',
                obj.lab, obj.volume, obj.allocation.path
            )
            obj.update_usage_attr(quota_b_attrtype, obj.total_usage_entry['total_size'])
            obj.update_usage_attr(quota_tb_attrtype, obj.total_usage_tb)

            logger.info('allocation usage for allocation %s: %s bytes, %s terabytes',
                obj.allocation.pk, obj.total_usage_entry['total_size'], obj.total_usage_tb
            )
            # identify and remove allocation users that are no longer in the AD group
            self.zero_out_absent_allocationusers(obj.query_usernames, obj.allocation)

            for userdict in obj.user_usage_entries:
                user = next(
                    u for u in user_models if userdict['username'].lower() == u.username.lower()
                )
                logger.debug('entering for user: %s', user.username)
                usage_bytes = int(userdict['size_sum'])
                usage, unit = determine_size_fmt(userdict['size_sum'])

                obj.update_user_usage(user, usage_bytes, usage, unit)
                logger.debug('saving %s', userdict)

    def zero_out_absent_allocationusers(self, redash_usernames, allocation):
        """Change usage of AllocationUsers not in StarfishRedash usage stats to 0.
        """
        allocationusers_not_in_redash = allocation.allocationuser_set.exclude(
            user__username__in=redash_usernames
        )
        if allocationusers_not_in_redash:
            logger.info(
                'users no longer in allocation %s: %s',
                allocation.pk, [user.user.username for user in allocationusers_not_in_redash]
            )
            allocationusers_not_in_redash.update(usage=0, usage_bytes=0)
