from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings

USERSYNC_ENABLE_SIGNALS = import_from_settings('USERSYNC_ENABLE_SIGNALS', False)

class UserSyncConfig(AppConfig):
    name = 'coldfront.plugins.user_sync'

    def ready(self):
        if USERSYNC_ENABLE_SIGNALS:
            import coldfront.plugins.user_sync.signals
