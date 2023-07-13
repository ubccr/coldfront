import logging
import requests
from requests.auth import HTTPBasicAuth

from coldfront.core.utils.common import import_from_settings


def get_scale_management_context():
    context = {}
    system_monitor = ScaleManagement()
    system_monitor.getExample()
    context['data'] = system_monitor.getResponse()

    return context


class ScaleManagement:
    """If anything fails, the home page will still work"""
    primary_color = '#002f56'
    info_color = '#2f9fd0'
    secondary_color = '#666666'

    def __init__(self):
        self.response = None
        self.data = {}
        self.getExample()

    def getExample(self):
        logging.debug('getting data')

        try:
            response = requests.get('https://storage1-gui1.ris.wustl.edu/scalemgmt/v2/filesystems/rdcw-fs1/quotas?fields=blockQuota,blockUsage,objectName', auth = HTTPBasicAuth('user', 'pass'))
        except Exception as e:
            response = None

        if response and response.status_code == 200:
            self.response = response    

    def getResponse(self):
        return self.response                      

