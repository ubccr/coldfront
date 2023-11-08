import logging
import json
import xml.etree.ElementTree as ET

import requests
from requests.auth import HTTPBasicAuth

from coldfront.core.utils.common import import_from_settings

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

class XdmodError(Exception):
    pass

class XdmodNotFoundError(XdmodError):
    pass

class XDModFetcher:

    def __init__(self, start, end, resources=None,):
        self.url = f'{XDMOD_API_URL}{_ENDPOINT_CORE_HOURS}'
        if resources is None:
            resources = []

        payload = _DEFAULT_PARAMS
        payload['start_date'] = start
        payload['end_date'] = end
        payload['resource_filter'] = f'"{",".join(resources)}"'
        payload['operation'] = 'get_data'
        self.payload = payload

    def fetch_data(self, search_item, payload):
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
                f'Rows not found for {search_item} - {self.payload["resources"]}'
            )
        cells = rows.find('row').findall('cell')
        if len(cells) != 2:
            raise XdmodError('Invalid XML data returned from XDMoD API: Cells not found')

        stats = cells[1].find('value').text
        return stats

    def xdmod_fetch_total_cpu_hours(self, account, statistics='total_cpu_hours'):
        """fetch total cpu hours."""
        payload = dict(self.payload)
        payload['pi_filter'] = f'"{account}"'
        payload['group_by'] = 'pi'
        payload['realm'] = 'Jobs'
        payload['statistic'] = statistics

        core_hours = self.fetch_data(account, payload)
        return core_hours

    def xdmod_fetch_total_storage(self, account, statistics='physical_usage'):
        """fetch total storage."""
        payload = dict(self.payload)
        payload['pi_filter'] = f'"{account}"'
        payload['group_by'] = 'pi'
        payload['realm'] = 'Storage'
        payload['statistic'] = statistics

        stats = self.fetch_data(account, payload)
        physical_usage = float(stats) / 1E9
        return physical_usage

    def xdmod_fetch_cloud_core_time(self, project):
        """fetch cloud core time."""
        payload = dict(self.payload)
        payload['project_filter'] = project
        payload['group_by'] = 'project'
        payload['realm'] = 'Cloud'
        payload['statistic'] = 'cloud_core_time'

        core_hours = self.fetch_data(project, payload)
        return core_hours
