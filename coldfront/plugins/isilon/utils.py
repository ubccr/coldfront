import isilon_sdk.v9_5_0
from isilon_sdk.v9_5_0.rest import ApiException

from coldfront.config.env import ENV
from coldfront.core.utils.common import import_from_settings

def connect():
    configuration = isilon_sdk.v9_5_0.Configuration()
    configuration.host = 'http://holy-isilon01.rc.fas.harvard.edu:8080'
    configuration.username = import_from_settings('ISILON_USER')
    configuration.password = import_from_settings('ISILON_PASS')
    configuration.verify_ssl = False
    api_client = isilon_sdk.v9_5_0.ApiClient(configuration)
    api_instance = isilon_sdk.v9_5_0.ProtocolsApi(api_client)
    return api_instance
