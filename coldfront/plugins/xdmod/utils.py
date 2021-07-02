import logging
import requests
import json
import xml.etree.ElementTree as ET

from coldfront.core.utils.common import import_from_settings

XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME = import_from_settings('XDMOD_CLOUD_PROJECT_ATTRIBUTE_NAME', 'Cloud Account Name')
XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME = import_from_settings('XDMOD_CLOUD_CORE_TIME_ATTRIBUTE_NAME', 'Core Usage (Hours)')
XDMOD_ACCOUNT_ATTRIBUTE_NAME = import_from_settings('XDMOD_ACCOUNT_ATTRIBUTE_NAME', 'slurm_account_name')
XDMOD_RESOURCE_ATTRIBUTE_NAME = import_from_settings('XDMOD_RESOURCE_ATTRIBUTE_NAME', 'xdmod_resource')
XDMOD_CPU_HOURS_ATTRIBUTE_NAME = import_from_settings('XDMOD_CPU_HOURS_ATTRIBUTE_NAME', 'Core Usage (Hours)')
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

def xdmod_fetch_total_cpu_hours(start, end, account, resources=None):
    if resources is None:
        resources = []

    url = '{}{}'.format(XDMOD_API_URL, _ENDPOINT_CORE_HOURS)
    payload = _DEFAULT_PARAMS
    payload['pi_filter'] = '"{}"'.format(account)
    payload['resource_filter'] = '"{}"'.format(','.join(resources))
    payload['start_date'] = start
    payload['end_date'] = end
    payload['group_by'] = 'pi'
    payload['realm'] = 'Jobs'
    payload['operation'] = 'get_data'
    payload['statistic'] = 'total_cpu_hours'
    r = requests.get(url, params=payload)

    logger.info(r.url)
    logger.info(r.text)

    try:
        error = r.json()
        # XXX fix me. Here we assume any json response is bad as we're
        # expecting xml but XDMoD should just return json always. 
        raise XdmodNotFoundError('Got json response but expected XML: {}'.format(error))
    except json.decoder.JSONDecodeError as e:
        pass

    try:
        root = ET.fromstring(r.text)
    except ET.ParserError as e:
        raise XdmodError('Invalid XML data returned from XDMoD API: {}'.format(e))

    rows = root.find('rows')
    if len(rows) != 1:
        raise XdmodNotFoundError('Rows not found for {} - {}'.format(account, resources))

    cells = rows.find('row').findall('cell')
    if len(cells) != 2:
        raise XdmodError('Invalid XML data returned from XDMoD API: Cells not found')

    core_hours = cells[1].find('value').text

    return core_hours

def xdmod_fetch_cloud_core_time(start, end, project, resources=None):
    if resources is None:
        resources = []

    url = '{}{}'.format(XDMOD_API_URL, _ENDPOINT_CORE_HOURS)
    payload = _DEFAULT_PARAMS
    payload['project_filter'] = project
    payload['resource_filter'] = '"{}"'.format(','.join(resources))
    payload['start_date'] = start
    payload['end_date'] = end
    payload['group_by'] = 'project'
    payload['realm'] = 'Cloud'
    payload['operation'] = 'get_data'
    payload['statistic'] = 'cloud_core_time'
    r = requests.get(url, params=payload)

    logger.info(r.url)
    logger.info(r.text)

    try:
        error = r.json()
        # XXX fix me. Here we assume any json response is bad as we're
        # expecting xml but XDMoD should just return json always. 
        raise XdmodNotFoundError('Got json response but expected XML: {}'.format(error))
    except json.decoder.JSONDecodeError as e:
        pass

    try:
        root = ET.fromstring(r.text)
    except ET.ParserError as e:
        raise XdmodError('Invalid XML data returned from XDMoD API: {}'.format(e))

    rows = root.find('rows')
    if len(rows) != 1:
        raise XdmodNotFoundError('Rows not found for {} - {}'.format(project, resources))

    cells = rows.find('row').findall('cell')
    if len(cells) != 2:
        raise XdmodError('Invalid XML data returned from XDMoD API: Cells not found')

    core_hours = cells[1].find('value').text

    return core_hours
