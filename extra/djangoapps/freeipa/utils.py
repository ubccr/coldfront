from django.core.exceptions import ImproperlyConfigured
from common.djangolibs.utils import import_from_settings

from ipalib import api

CLIENT_KTNAME = import_from_settings('FREEIPA_KTNAME')
UNIX_GROUP_ATTRIBUTE_NAME = import_from_settings('FREEIPA_GROUP_ATTRIBUTE_NAME', 'freeipa_group')

try:
    api.bootstrap()
    api.finalize()
    api.Backend.rpcclient.connect()
except Exception as e:
    logger.error("Failed to initialze FreeIPA lib: %s", e)
    raise ImproperlyConfigured('Failed to initialze FreeIPA: {0}'.format(e))

def check_ipa_group_error(res):
    if not res:
        raise ValueError('Missing FreeIPA response')

    if res['completed'] == 1:
        return

    user = res['failed']['member']['user'][0][0]
    group = res['result']['cn'][0]
    err_msg = res['failed']['member']['user'][0][1]

    # If user is already a member don't error out. Silently ignore
    if err_msg == 'This entry is already a member':
        logger.warn("User %s is already a member of group %s", user, group)
        return

    raise Exception(err_msg)
