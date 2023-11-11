import logging
import json
import xml.etree.ElementTree as ET

import requests
from requests.auth import HTTPBasicAuth

from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.fasrc import get_quarter_start_end


XDMOD_USER = import_from_settings('XDMOD_USER', '')
XDMOD_PASS = import_from_settings('XDMOD_PASS', '')

XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME', 'Cloud Account Name')
XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME', 'Core Usage (Hours)')

XDMOD_ACCOUNT_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_ACCOUNT_ATTRIBUTE_NAME', 'slurm_account_name')

XDMOD_RESOURCE_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_RESOURCE_ATTRIBUTE_NAME', 'xdmod_resource')

XDMOD_CPU_HOURS_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_CPU_HOURS_ATTRIBUTE_NAME', 'Core Usage (Hours)')
XDMOD_ACC_HOURS_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_ACC_HOURS_ATTRIBUTE_NAME', 'Accelerator Usage (Hours)')

XDMOD_STORAGE_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_STORAGE_ATTRIBUTE_NAME', 'Storage Quota (GB)')
XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME = import_from_settings(
    'XDMOD_STORAGE_GROUP_ATTRIBUTE_NAME', 'Storage_Group_Name')

XDMOD_API_URL = import_from_settings('XDMOD_API_URL')

_ENDPOINT_CORE_HOURS = '/controllers/user_interface.php'

_DEFAULT_PARAMS = {
    'aggregation_unit': 'Auto',
    'display_type': 'bar',
    'format': 'xml',
    'operation': 'get_data',
    'public_user': 'true',
    'query_group': 'tg_usage',
}

logger = logging.getLogger(__name__)

QUARTER_START, QUARTER_END = get_quarter_start_end()


class XdmodError(Exception):
    pass

class XdmodNotFoundError(XdmodError):
    pass

class XDModFetcher:
    def __init__(self, start=QUARTER_START, end=QUARTER_END, resources=None):
        self.url = f'{XDMOD_API_URL}{_ENDPOINT_CORE_HOURS}'
        if resources is None:
            resources = []

        payload = _DEFAULT_PARAMS
        payload['start_date'] = start
        payload['end_date'] = end
        payload['resource_filter'] = f'"{",".join(resources)}"'
        payload['operation'] = 'get_data'
        self.payload = payload
        self.group_by = {'total':'pi', 'per-user':'user'}

    def fetch_data(self, payload, search_item=None):
        r = requests.get(
            self.url, params=payload, auth=HTTPBasicAuth(XDMOD_USER, XDMOD_PASS)
        )
        logger.info(r.url)
        logger.info(r.text)

        try:
            error = r.json()
            # XXXX fix me. Here we assume any json response is bad as we're
            # expecting xml but XDMoD should just return json always.
            raise XdmodNotFoundError(f'Got json response but expected XML: {error}')
        except json.decoder.JSONDecodeError as e:
            pass

        try:
            root = ET.fromstring(r.text)
        except ET.ParserError as e:
            raise XdmodError(f'Invalid XML data returned from XDMoD API: {e}') from e

        rows = root.find('rows')
        if len(rows) != 1:
            raise XdmodNotFoundError(
                f'Rows not found for {search_item} - {self.payload["resource_filter"]}'
            )
        cells = rows.find('row').findall('cell')
        if len(cells) != 2:
            raise XdmodError('Invalid XML data returned from XDMoD API: Cells not found')

        stats = cells[1].find('value').text
        return stats

    def xdmod_fetch(self, account, statistics, realm, group_by='total'):
        """fetch either total or per-user usage stats"""
        payload = dict(self.payload)
        payload['pi_filter'] = f'"{account}"'
        payload['group_by'] = self.group_by[group_by]
        payload['statistic'] = statistics
        payload['realm'] = realm
        core_hours = self.fetch_data(payload, search_item=account)
        return core_hours

    def xdmod_fetch_all_project_usages(self, statistic):
        """return usage statistics for all projects"""
        payload = dict(self.payload)
        payload['group_by'] = 'pi'
        payload['realm'] = 'Jobs'
        payload['statistic'] = statistic
        stats = self.fetch_data(payload)
        return stats

    def xdmod_fetch_cpu_hours(self, account, group_by='total', statistics='total_cpu_hours'):
        """fetch either total or per-user cpu hours"""
        core_hours = self.xdmod_fetch(account, statistics, 'Jobs', group_by=group_by)
        return core_hours

    def xdmod_fetch_storage(self, account, group_by='total', statistics='physical_usage'):
        """fetch total or per-user storage stats."""
        stats = self.xdmod_fetch(account, statistics, 'Storage', group_by=group_by)
        physical_usage = float(stats) / 1E9
        return physical_usage

    def xdmod_fetch_cloud_core_time(self, project):
        """fetch cloud core time."""
        payload = dict(self.payload)
        payload['project_filter'] = project
        payload['group_by'] = 'project'
        payload['realm'] = 'Cloud'
        payload['statistic'] = 'cloud_core_time'

        core_hours = self.fetch_data(payload, search_item=project)
        return core_hours
