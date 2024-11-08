from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings

SFUSER = import_from_settings('SFUSER')
SFPASS = import_from_settings('SFPASS')
SFSERVER = import_from_settings('SFSERVER')
SFDATAPATH = import_from_settings('SFDATAPATH')
REDASHKEY = import_from_settings('REDASHKEY')
COLDFRONT_HOST = import_from_settings('COLDFRONT_HOST')

class StarFishConfig(AppConfig):
    name = 'coldfront.plugins.sftocf'
