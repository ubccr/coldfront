# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.config.env import ENV

# ------------------------------------------------------------------------------
# Email/Notification settings
# ------------------------------------------------------------------------------
EMAIL_ENABLED = ENV.bool("EMAIL_ENABLED", default=False)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = ENV.str("EMAIL_HOST", default="localhost")
EMAIL_PORT = ENV.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = ENV.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = ENV.str("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = ENV.bool("EMAIL_USE_TLS", default=False)
EMAIL_TIMEOUT = ENV.int("EMAIL_TIMEOUT", default=3)
EMAIL_SUBJECT_PREFIX = ENV.str("EMAIL_SUBJECT_PREFIX", default="[ColdFront]")
EMAIL_SENDER = ENV.str("EMAIL_SENDER", default="")
EMAIL_SIGNATURE = ENV.str("EMAIL_SIGNATURE", default="", multiline=True)
