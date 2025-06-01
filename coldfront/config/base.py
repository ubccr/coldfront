# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Base Django settings for ColdFront project.
"""

import importlib.util
import os
import sys

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

import coldfront
from coldfront.config.env import ENV, PROJECT_ROOT

# ------------------------------------------------------------------------------
# Base Django config for ColdFront
# ------------------------------------------------------------------------------
VERSION = coldfront.VERSION
BASE_DIR = PROJECT_ROOT()
ALLOWED_HOSTS = ENV.list("ALLOWED_HOSTS", default=["*"])
DEBUG = ENV.bool("DEBUG", default=False)
WSGI_APPLICATION = "coldfront.config.wsgi.application"
ROOT_URLCONF = "coldfront.config.urls"

SECRET_KEY = ENV.str("SECRET_KEY", default="")
if len(SECRET_KEY) == 0:
    SECRET_KEY = get_random_secret_key()

# ------------------------------------------------------------------------------
# Locale settings
# ------------------------------------------------------------------------------
LANGUAGE_CODE = ENV.str("LANGUAGE_CODE", default="en-us")
TIME_ZONE = ENV.str("TIME_ZONE", default="America/New_York")
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ------------------------------------------------------------------------------
# Django Apps
# ------------------------------------------------------------------------------

# See: https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys
# We should change this to BigAutoField at some point
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

# Additional Apps
# Hack to fix fontawesome. Will be fixed in version 6
sys.modules["fontawesome_free"] = __import__("fontawesome-free")
INSTALLED_APPS += [
    "crispy_forms",
    "crispy_bootstrap4",
    "django_q",
    "simple_history",
    "fontawesome_free",
]

if DEBUG and importlib.util.find_spec("sslserver") is not None:
    INSTALLED_APPS += [
        "sslserver",
    ]

# ColdFront Apps
INSTALLED_APPS += [
    "coldfront.core.user",
    "coldfront.core.field_of_science",
    "coldfront.core.utils",
    "coldfront.core.portal",
    "coldfront.core.project",
    "coldfront.core.resource",
    "coldfront.core.allocation",
    "coldfront.core.grant",
    "coldfront.core.publication",
    "coldfront.core.research_output",
]

# ------------------------------------------------------------------------------
# Django Middleware
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

# ------------------------------------------------------------------------------
# Django authentication backend. See auth.py
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = []

# ------------------------------------------------------------------------------
# Django Q
# ------------------------------------------------------------------------------
Q_CLUSTER = {
    "timeout": ENV.int("Q_CLUSTER_TIMEOUT", default=120),
    "retry": ENV.int("Q_CLUSTER_RETRY", default=120),
}


# ------------------------------------------------------------------------------
# Django template and site settings
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            PROJECT_ROOT("site/templates"),
            "/usr/share/coldfront/site/templates",
            PROJECT_ROOT("coldfront/templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django_settings_export.settings_export",
            ],
        },
    },
]

# Add local site templates files if set
SITE_TEMPLATES = ENV.str("SITE_TEMPLATES", default="")
if len(SITE_TEMPLATES) > 0:
    if os.path.isdir(SITE_TEMPLATES):
        TEMPLATES[0]["DIRS"].insert(0, SITE_TEMPLATES)
    else:
        raise ImproperlyConfigured("SITE_TEMPLATES should be a path to a directory")

CRISPY_TEMPLATE_PACK = "bootstrap4"
SETTINGS_EXPORT = []

STATIC_URL = "/static/"
STATIC_ROOT = ENV.str("STATIC_ROOT", default=PROJECT_ROOT("static_root"))
STATICFILES_DIRS = [
    PROJECT_ROOT("coldfront/static"),
]

# Add local site static files if set
SITE_STATIC = ENV.str("SITE_STATIC", default="")
if len(SITE_STATIC) > 0:
    if os.path.isdir(SITE_STATIC):
        STATICFILES_DIRS.insert(0, SITE_STATIC)
    else:
        raise ImproperlyConfigured("SITE_STATIC should be a path to a directory")

# Add system site static files
if os.path.isdir("/usr/share/coldfront/site/static"):
    STATICFILES_DIRS.insert(0, "/usr/share/coldfront/site/static")
