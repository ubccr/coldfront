from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings

SFUSER = import_from_settings('SFUSER')
SFPASS = import_from_settings('SFPASS')


class StarFishConfig(AppConfig):
    name = 'coldfront.plugins.sftocf'
