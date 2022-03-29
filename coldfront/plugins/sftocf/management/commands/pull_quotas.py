import os
import re
import json
import logging
import requests

from django.core.management.base import BaseCommand, CommandError

from coldfront.core.utils.common import import_from_settings
from coldfront.plugins.sftocf.pipeline import AllTheThingsConn
from coldfront.core.allocation.models import Allocation, AllocationAttribute

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    '''
    Collect usage data from Starfish and insert it into the Coldfront database.
    '''

    def handle(self, *args, **kwargs):
        attconn = AllTheThingsConn()
        attconn.pull_quota_data()
