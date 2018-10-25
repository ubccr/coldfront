from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings

FREEIPA_ENABLE_SIGNALS = import_from_settings('FREEIPA_ENABLE_SIGNALS', False)

class IPAConfig(AppConfig):
    name = 'coldfront.plugins.freeipa'

    def ready(self):
        if FREEIPA_ENABLE_SIGNALS:
            import coldfront.plugins.freeipa.signals
