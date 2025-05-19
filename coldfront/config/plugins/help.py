from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV
from coldfront.core.utils.common import import_from_settings

INSTALLED_APPS += [
    'coldfront.plugins.help',
]

SUPPORT_EMAILS = sorted(import_from_settings('SUPPORT_EMAILS', []), key=lambda x: x["title"])
EMAIL_HELP_TEMPLATE = ENV.str("EMAIL_HELP_TEMPLATE")
EMAIL_HELP_DEFAULT_TARGET = ENV.str("EMAIL_HELP_DEFAULT_TARGET")

