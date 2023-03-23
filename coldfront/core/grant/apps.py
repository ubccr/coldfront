from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings
GRANT_ENABLE = import_from_settings('GRANT_ENABLE', False)

if GRANT_ENABLE:
    class GrantConfig(AppConfig):
        name = 'coldfront.core.grant'
