from coldfront.plugins.fasrc.utils import pull_push_quota_data
import logging
from django.core import management


def import_quotas(volumes=None):
    """
    Collect group-level quota and usage data from ATT and NESE and insert it
    into the Coldfront database.

    Parameters
    ----------
    volumes : string of volume names separated by commas. Optional, default None
    """
    logger = logging.getLogger('coldfront.import_quotas')
    if volumes:
        volumes = volumes.split(",")
    pull_push_quota_data()

def id_import_allocations():
    """ID and import new allocations using ATT and Starfish data
    """
    management.call_command('id_import_new_allocations')
