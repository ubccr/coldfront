import os
import re
import json
import logging
import requests

from django.core.management.base import BaseCommand, CommandError

from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.fasrc.utils import AllTheThingsConn
from coldfront.core.allocation.models import Allocation, AllocationAttribute

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    '''
    Collect usage data from Starfish and insert it into the Coldfront database.
    '''

    def handle(self, *args, **kwargs):
        attconn = AllTheThingsConn()
        result_file = attconn.pull_quota_data()
        # result_file = "coldfront/plugins/fasrc/data/allthethings_output.json"
        attconn.push_quota_data(result_file)
