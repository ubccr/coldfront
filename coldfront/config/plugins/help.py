from coldfront.config.base import INSTALLED_APPS
from coldfront.config.env import ENV

INSTALLED_APPS += [
    "coldfront.plugins.help",
]

EMAIL_HELP_SUPPORT_EMAILS = ENV.dict("EMAIL_HELP_SUPPORT_EMAILS", default={})
EMAIL_HELP_TEMPLATE = ENV.str(
    "EMAIL_HELP_TEMPLATE", default="Name:\n{first} {last}\n\nMessage:\n{message}\n"
)
EMAIL_HELP_DEFAULT_EMAIL = ENV.str("EMAIL_HELP_DEFAULT_EMAIL")
