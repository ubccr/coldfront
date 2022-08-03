from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings


class FASRCConfig(AppConfig):
    name = 'coldfront.plugins.fasrc'
