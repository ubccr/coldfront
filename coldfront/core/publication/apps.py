from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings
PUBLICATION_ENABLE = import_from_settings('PUBLICATION_ENABLE', False)

if PUBLICATION_ENABLE:
    class PublicationConfig(AppConfig):
        name = 'coldfront.core.publication'
