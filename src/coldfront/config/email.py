# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.config.env import ENV

# ------------------------------------------------------------------------------
# Email/Notification settings
# ------------------------------------------------------------------------------
# Django 6.1 mailer configuration. The deprecated EMAIL_* SMTP settings
# are replaced by the nested MAILERS structure.
MAILERS = {
    "default": {
        "BACKEND": ENV.str("MAILER_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"),
        #        "OPTIONS": {
        #            "host": ENV.str("MAILER_HOST", default="localhost"),
        #            "port": ENV.int("MAILER_PORT", default=25),
        #            "username": ENV.str("MAILER_USER", default=""),
        #            "password": ENV.str("MAILER_PASSWORD", default=""),
        #            "use_tls": ENV.bool("MAILER_USE_TLS", default=False),
        #            "timeout": ENV.int("MAILER_TIMEOUT", default=3),
        #        },
    },
}

EMAIL_SUBJECT_PREFIX = ENV.str("EMAIL_SUBJECT_PREFIX", default="[ColdFront]")
EMAIL_SENDER = ENV.str("EMAIL_SENDER", default="")
EMAIL_SIGNATURE = ENV.str("EMAIL_SIGNATURE", default="", multiline=True)
