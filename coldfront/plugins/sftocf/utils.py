from functools import reduce
import logging
from itertools import groupby
import operator
from django.db.models import Q

from django.contrib.auth import get_user_model
from django.dispatch import receiver
from coldfront.core.allocation.signals import allocation_activate
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.local_utils import (
    read_json,
    log_missing,
    determine_size_fmt,
    locate_or_create_dirpath,
)
from coldfront.plugins.sftocf.pipeline import RedashDataPipeline
from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttributeType,
    Resource
)
from coldfront.plugins.sftocf.allocation_query_match import AllocationQueryMatch

DATAPATH = './coldfront/plugins/sftocf/data/'

logger = logging.getLogger(__name__)

svp = read_json('coldfront/plugins/sftocf/servers.json')

username_ignore_list = import_from_settings('username_ignore_list', [])

locate_or_create_dirpath(DATAPATH)

def record_process(func):
    """Wrapper function for logging"""
    def call(*args, **kwargs):
        funcdata = '{} {}'.format(func.__name__, func.__code__.co_firstlineno)
        logger.debug('\n%s START.', funcdata)
        result = func(*args, **kwargs)
        logger.debug('%s END. output:\n%s\n', funcdata, result)
        return result
    return call


def return_dict_of_groupings(dict_list, sort_key):
    """Given a list of dicts, return a dict of lists of dicts grouped by the
    key(s) given in sort_key.
    """
    grouped = groupby(sorted(dict_list, key=sort_key), key=sort_key)
    return {k: list(g) for k, g in grouped}


def get_corresponding_coldfront_resources(volume_list):
    resources = Resource.objects.filter(
        reduce(operator.or_,(Q(name__contains=x) for x in volume_list))
    )
    return resources

def get_volumes_in_coldfront(volume_list):
    resource_volume_list = [r.name.split('/')[0] for r in Resource.objects.all()]
    return [v for v in volume_list if v in resource_volume_list]


def handle_vol_query_result(vol_query_result, resource_names):
    result = vol_query_result['query_result']['data']['rows']
    result = [{
        k.replace(' ', '_').replace('(','').replace(')','') : v for k, v in d.items()
    } for d in result]
    #resource_names = [
    #    n.split('/')[0] for n in Resource.objects.values_list('name',flat=True)
    #]
    return [r for r in result if r['volume_name'] in resource_names]


def handle_path_usage_query_result(path_usage_query_result, volumes=None):
    """Return query results.
    """
    result = path_usage_query_result
    if 'query_result' in result and result['query_result']:
        data = result['query_result']['data']['rows']
    else:
        print('no query_result value found:\n', result)
    if volumes:
        data = [d for d in data if d['vol_name'] in volumes]
    return data


@receiver(allocation_activate)
def update_allocation(sender, **kwargs):
    '''update the allocation data when the allocation is activated.'''
    logger.debug('allocation_activate signal received')
    allocation = Allocation.objects.get(pk=kwargs['allocation_pk'])
    volume_name = allocation.resources.first().name.split('/')[0]
    sf_redash_data = RedashDataPipeline(volume=volume_name)
    user_data, allocation_data = sf_redash_data.collect_sf_data_for_lab(
        allocation.project.title, volume_name
    )
    if not allocation_data:
        raise ValueError('No matching allocation found for the given data.')
    subdir_type = AllocationAttributeType.objects.get(name='Subdirectory')
    allocation.allocationattribute_set.get_or_create(
        allocation_attribute_type_id=subdir_type.pk,
        value=allocation_data[0]['path']
    )

    allocation_query_match = AllocationQueryMatch(allocation, allocation_data, user_data)

    quota_b_attrtype = AllocationAttributeType.objects.get(name='Quota_In_Bytes')
    quota_tb_attrtype = AllocationAttributeType.objects.get(name='Storage Quota (TB)')

    allocation_query_match.update_usage_attr(quota_b_attrtype, allocation_query_match.total_usage_entry['total_size'])
    allocation_query_match.update_usage_attr(quota_tb_attrtype, allocation_query_match.total_usage_tb)
    missing_users = []
    for userdict in allocation_query_match.user_usage_entries:
        try:
            user = get_user_model().objects.get(username=userdict['username'])
        except get_user_model().DoesNotExist:
            missing_users.append({
                'username': userdict['username'],
                'volume': userdict.get('volume', None),
                'path': userdict.get('path', None)
            })
            continue
        usage_bytes = int(userdict['size_sum'])
        usage, unit = determine_size_fmt(userdict['size_sum'])
        allocation_query_match.update_user_usage(user, usage_bytes, usage, unit)
    if missing_users:
        log_missing('user', missing_users)

