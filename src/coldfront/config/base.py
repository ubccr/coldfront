# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Base Django settings for ColdFront project.
"""

import importlib.util
import os

from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key
from django.utils.translation import gettext_lazy as _

import coldfront
from coldfront.config.env import ENV, PROJECT_ROOT

# ------------------------------------------------------------------------------
# Base Django config for ColdFront
# ------------------------------------------------------------------------------
VERSION = coldfront.VERSION

BASE_PATH = ENV.str("BASE_PATH", default="")
if len(BASE_PATH) > 0:
    BASE_PATH = f"{BASE_PATH.strip('/')}/"

BASE_DIR = PROJECT_ROOT()
DEBUG = ENV.bool("DEBUG", default=False)
WSGI_APPLICATION = "coldfront.config.wsgi.application"
ROOT_URLCONF = "coldfront.config.urls"

ALLOWED_HOSTS = ENV.list("ALLOWED_HOSTS", default=[])
if not ALLOWED_HOSTS:
    if DEBUG:
        ALLOWED_HOSTS = ["*"]
    else:
        raise ImproperlyConfigured("Required setting ALLOWED_HOSTS is not defined.")

SECRET_KEY = ENV.str("SECRET_KEY", default="")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = get_random_secret_key()
    else:
        raise ImproperlyConfigured("Required setting SECRET_KEY is not defined.")


# ------------------------------------------------------------------------------
# Locale settings
# ------------------------------------------------------------------------------
LANGUAGE_CODE = ENV.str("LANGUAGE_CODE", default="en-us")
TIME_ZONE = ENV.str("TIME_ZONE", default="America/New_York")
USE_I18N = True
USE_TZ = True

LANGUAGES = (("en", _("English")),)
LOCALE_PATHS = (BASE_DIR + "/coldfront/translations",)

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
    "django.forms",
]

INSTALLED_APPS += [
    "crispy_forms",
    "crispy_bootstrap5",
    "django_vite",
    "django_htmx",
    "django_tables2",
    "django_jsonform",
    "django_cotton.apps.SimpleAppConfig",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "social_django",
    "generic_notifications",
    "django_rq",
    "djmoney",
]

if DEBUG and importlib.util.find_spec("sslserver") is not None:
    INSTALLED_APPS += [
        "sslserver",
    ]

# ColdFront Apps
INSTALLED_APPS += [
    "coldfront.users",
    "coldfront.core",
    "coldfront.account",
    "coldfront.tenancy",
    "coldfront.ras",
    "coldfront.slurm",
    "coldfront.storage",
    "coldfront.ris",
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
    "django_htmx.middleware.HtmxMiddleware",
    "coldfront.auth.middleware.RemoteUserMiddleware",
    "coldfront.middleware.ColdFrontMiddleware",
    "coldfront.auth.middleware.HtmxAuthRedirectMiddleware",
]

# ------------------------------------------------------------------------------
# Django authentication backend. See auth.py
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = []

# ------------------------------------------------------------------------------
# Django Tasks (background job framework)
# ------------------------------------------------------------------------------
# ColdFrontBackend handles queueing either directly via the Job model (DB
# backend, default) or by delegating to django-tasks-rq (RQ backend).
#
# COLDFRONT_TASKS_BACKEND selects which path to use:
#   "django_tasks_db.backend.DatabaseBackend"  — ORM-based (default, no Redis)
#   "django_tasks_rq.backend.RQBackend"        — Redis-based via django-rq
#
# For the DB path, ColdFrontBackend uses the Job model as the queue record.
# No separate DBTaskResult is created — the Job IS the queue entry.

COLDFRONT_TASKS_BACKEND = ENV.str(
    "COLDFRONT_TASKS_BACKEND",
    default="django_tasks_db.backend.DatabaseBackend",
)

TASKS = {
    "default": {
        "BACKEND": "coldfront.core.tasks.backends.ColdFrontBackend",
        "QUEUES": [],
    },
    "immediate": {
        "BACKEND": "django_tasks.backends.immediate.ImmediateBackend",
    },
    "dummy": {
        "BACKEND": "django_tasks.backends.dummy.DummyBackend",
    },
}

# ------------------------------------------------------------------------------
# RQ (Redis Queue) connection settings
# ------------------------------------------------------------------------------
# These are passed to django-rq for configuring the Redis connection.
# Required when COLDFRONT_TASKS_BACKEND uses the RQ backend.

RQ = {
    "HOST": ENV.str("RQ_REDIS_HOST", default=ENV.str("REDIS_HOST", default="localhost")),
    "PORT": ENV.int("RQ_REDIS_PORT", default=ENV.int("REDIS_PORT", default=6379)),
    "DB": ENV.int("RQ_REDIS_DATABASE", default=8),
    "USERNAME": ENV.str("RQ_REDIS_USERNAME", default=""),
    "PASSWORD": ENV.str("RQ_REDIS_PASSWORD", default=""),
    "DEFAULT_TIMEOUT": ENV.int("RQ_DEFAULT_TIMEOUT", default=300),
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
        "OPTIONS": {
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django_cotton.cotton_loader.Loader",
                        "django.template.loaders.filesystem.Loader",
                    ],
                )
            ],
            "builtins": [
                "coldfront.core.templatetags.builtins.filters",
                "coldfront.core.templatetags.builtins.tags",
                "django_cotton.templatetags.cotton",
            ],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "coldfront.context_processors.settings",
                "coldfront.context_processors.registry",
                "coldfront.context_processors.unread_notifications_count",
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

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# This allows us to override Django's stock form widget templates
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

SETTINGS_EXPORT = []

STATIC_URL = f"/{BASE_PATH}static/"

DJANGO_VITE = {
    "default": {
        "dev_mode": ENV.bool("DJANGO_VITE_DEV_MODE", default=False),
        "dev_server_port": ENV.int("DJANGO_VITE_SERVER_PORT", default=5173),
    }
}

if DEBUG and not DJANGO_VITE["default"]["dev_mode"]:
    DJANGO_VITE["default"]["manifest_path"] = PROJECT_ROOT("coldfront/static/bundles/manifest.json")

STATIC_ROOT = ENV.str("STATIC_ROOT", default=PROJECT_ROOT("static_root"))
STATICFILES_DIRS = [
    PROJECT_ROOT("coldfront/static/bundles"),
    PROJECT_ROOT("coldfront/static/assets"),
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

# This silences the following Django warning:
#
#   (fields.W342) Setting unique=True on a ForeignKey has the same effect as using a OneToOneField.
#   HINT: ForeignKey(unique=True) is usually   better served by a OneToOneField.
#
# ColdFront uses ForeignKey(unique=True) on certain AllocatableResource app
# models that require a link to ras.Allocation for storing custom allocation
# data. Using ForeignKey instead of OneToOneField is necessary for the
# "related_models" feature so these models show up in the UI for Allocations
# under "Related".
SILENCED_SYSTEM_CHECKS = ["fields.W342"]
