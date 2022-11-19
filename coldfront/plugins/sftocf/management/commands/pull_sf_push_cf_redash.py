import re
import logging
from datetime import datetime, timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from coldfront.core.utils.fasrc import determine_size_fmt
from coldfront.core.project.models import Project, ProjectUser, ProjectUserStatusChoice
from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import Allocation, AllocationUser, AllocationUserStatusChoice
from coldfront.plugins.sftocf.utils import StarFishRedash, svp, log_missing_user_models


datestr = datetime.today().strftime('%Y%m%d')
logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler(f'logs/starfish_to_coldfront_{datestr}.log', 'w')
logger.addHandler(filehandler)


class Command(BaseCommand):
    '''
    Collect usage data from Starfish and insert it into the Coldfront database.
    '''

    def handle(self, *args, **kwargs):
        '''
        Query Starfish Redash API for user usage data and update Coldfront AllocationUser entries.

        Only Projects that are already in Coldfront will get updated.

        Assumptions this code relies on:
        1. A project cannot have multiple allocations on the same storage resource.
        '''

        # 1. produce list of all volumes to be collected
        vol_set = [re.sub(r'\/.+','',n) for n in Resource.objects.values_list('name', flat=True)]
        vols_to_collect = [v for v in svp['volumes'].keys() for vol in vol_set if vol == v]

        # 2. grab data from redash
        redash_api = StarFishRedash(svp['server'])
        user_usage = redash_api.get_usage_stats(volumes=vols_to_collect)
        queryset = []
        # 3. iterate across all allocations
        for allocation in Allocation.objects.all():
            project = allocation.project
            lab = project.title
            resource = allocation.get_resources_as_string.split(', ')[0]
            volume = resource.split('/')[0]

            lab_data = [i for i in user_usage if i['group_name'] == lab and i['vol_name'] == volume]
            if not lab_data:
                print('No starfish result for', lab, resource)
                logger.warning('WARNING: No starfish result for %s %s', lab, resource)
                continue

            usernames = [d['user_name'] for d in lab_data]

            user_models = get_user_model().objects.filter(username__in=usernames)
            log_missing_user_models(lab, user_models, usernames)
            logger.debug('%s\n usernames: %s\n user_models: %s',
                    project.title, usernames, [u.username for u in user_models])

            for user in user_models:
                userdict = next(d for d in lab_data if d['user_name'] == user.username)
                logger.debug('entering for user: %s', user.username)
                try:
                    allocationuser = AllocationUser.objects.get(
                        allocation=allocation, user=user
                    )
                except AllocationUser.DoesNotExist:
                    if userdict['size_sum'] > 0:
                        allocationuser = AllocationUser.objects.create(
                            allocation=allocation,
                            created=timezone.now(),
                            status=AllocationUserStatusChoice.objects.get(name='Active'),
                            user=user
                        )
                    else:
                        print("allocation user missing:", lab, resource, userdict)
                        continue
                size_sum = int(userdict['size_sum'])
                usage, unit = determine_size_fmt(userdict['size_sum'])
                allocationuser.usage_bytes = size_sum
                allocationuser.usage = usage
                allocationuser.unit = unit
                queryset.append(allocationuser)
                # automatically update 'modified' field & add old record to history
                logger.debug("saving %s",userdict)
        AllocationUser.objects.bulk_update(queryset, ['usage_bytes', 'usage', 'unit'])
