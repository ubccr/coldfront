import logging
import json
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from coldfront.core.utils.common import import_from_settings

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

def get_quarter_start_end():
    y = datetime.today().year
    quarter_starts = [f'{y}-01-01', f'{y}-04-01', f'{y}-07-01', f'{y}-10-01']
    quarter_ends = [f'{y}-03-31', f'{y}-06-30', f'{y}-09-30', f'{y}-12-31']
    quarter = (datetime.today().month-1)//3
    return (quarter_starts[quarter], quarter_ends[quarter])

QUARTER_START, QUARTER_END = get_quarter_start_end()

logger = logging.getLogger(__name__)

class XdmodError(Exception):
    pass

class XdmodNotFoundError(XdmodError):
    pass

class XDModFetcher:
    def __init__(self, start=QUARTER_START, end=QUARTER_END, resources=None):
        self.url = f'{XDMOD_API_URL}{_ENDPOINT_CORE_HOURS}'
        self.resources = resources
        payload = _DEFAULT_PARAMS
        payload['start_date'] = start
        payload['end_date'] = end
        if resources:
            payload['resource_filter'] = f'"{",".join(resources)}"'
        self.payload = payload
        self.group_by = {'total':'pi', 'per-user':'person'}

    def fetch_data(self, payload, search_item=None):
        r = requests.get(self.url, params=payload)
        logger.info(r.url)
        logger.info(r.text)

        try:
            error = r.json()
            raise XdmodNotFoundError(f'Got json response but expected XML: {error}')
        except json.decoder.JSONDecodeError as e:
            pass

        try:
            root = ET.fromstring(r.text)
        except ET.ParserError as e:
            raise XdmodError(f'Invalid XML data returned from XDMoD API: {e}') from e

        rows = root.find('rows')
        if len(rows) < 1:
            raise XdmodNotFoundError(
                f'Rows not found for {search_item} - {self.payload["resource_filter"]}'
            )
        return rows

    def fetch_value(self, payload, search_item=None):
        rows = self.fetch_data(payload, search_item=search_item)
        cells = rows.find('row').findall('cell')
        if len(cells) != 2:
            raise XdmodError('Invalid XML data returned from XDMoD API: Cells not found')
        stats = cells[1].find('value').text
        return stats

    def fetch_table(self, payload, search_item=None):
        """make a dictionary of usernames and their associated core hours from
        XML data.
        """
        # return rows extracted from XML data
        rows = self.fetch_data(payload, search_item=search_item)
        # Produce a dict of usernames and their associated core hours from those rows
        stats = {}
        for row in rows:
            cells = row.findall('cell')
            username = cells[0].find('value').text
            stats[username] = cells[1].find('value').text
        return stats

    def xdmod_fetch(self, account, statistic, realm, start_date=None, end_date=None, group_by='total'):
        """fetch either total or per-user usage stats for specified project"""
        payload = dict(self.payload)
        payload['pi_filter'] = f'"{account}"'
        payload['group_by'] = self.group_by[group_by]
        payload['statistic'] = statistic
        payload['realm'] = realm
        if start_date:
            payload['start_date'] = start_date
        if end_date:
            payload['end_date'] = end_date
        if group_by == 'total':
            core_hours = self.fetch_value(payload, search_item=account)
        elif group_by == 'per-user':
            core_hours = self.fetch_table(payload, search_item=account)
        else:
            raise Exception('unrecognized group_by value')
        return core_hours

    def xdmod_fetch_all_project_usages(self, statistic):
        """return usage statistics for all projects"""
        payload = dict(self.payload)
        payload['group_by'] = 'pi'
        payload['realm'] = 'Jobs'
        payload['statistic'] = statistic
        stats = self.fetch_table(payload)
        return stats

    def xdmod_fetch_cpu_hours(self, account, start_date=None, end_date=None, group_by='total', statistics='total_cpu_hours'):
        """fetch either total or per-user cpu hours"""
        core_hours = self.xdmod_fetch(account, statistics, 'Jobs', start_date=start_date, end_date=end_date, group_by=group_by)
        return core_hours

    def xdmod_fetch_storage(self, account, start_date=None, end_date=None, group_by='total', statistic='physical_usage'):
        """fetch total or per-user storage stats."""
        stats = self.xdmod_fetch(account, statistic, 'Storage', start_date=start_date, end_date=end_date, group_by=group_by)
        physical_usage = float(stats) / 1E9
        return physical_usage

    def xdmod_fetch_cloud_core_time(self, project, start_date=None, end_date=None):
        """fetch cloud core time."""
        payload = dict(self.payload)
        payload['project_filter'] = project
        payload['group_by'] = 'project'
        payload['realm'] = 'Cloud'
        payload['statistic'] = 'cloud_core_time'
        if start_date:
            payload['start_date'] = start_date
        if end_date:
            payload['end_date'] = end_date

        core_hours = self.fetch_value(payload, search_item=project)
        return core_hours
