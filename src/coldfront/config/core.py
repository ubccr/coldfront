# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import coldfront
from coldfront.choices import parse_choices_from_env
from coldfront.config.env import ENV

# ------------------------------------------------------------------------------
# Advanced ColdFront configurations
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# General Center Information
# ------------------------------------------------------------------------------
CENTER_NAME = ENV.str("CENTER_NAME", default="HPC Center")
CENTER_HELP_URL = ENV.str("CENTER_HELP_URL", default="")
CENTER_PROJECT_RENEWAL_HELP_URL = ENV.str("CENTER_PROJECT_RENEWAL_HELP_URL", default="")
CENTER_BASE_URL = ENV.str("CENTER_BASE_URL", default="")

# Number of days to retain ObjectChange records before PruneChangeLogJob deletes
# them.  Set to 0 (or a negative value) to never delete changelog entries.
CHANGELOG_RETENTION = ENV.int("CHANGELOG_RETENTION", default=90)

# Number of days to retain completed Job records before prune_tasks deletes
# them.  Set to 0 (or a negative value) to keep completed jobs indefinitely.
JOB_COMPLETED_RETENTION = ENV.int("JOB_COMPLETED_RETENTION", default=90)

# Number of days to retain failed/errored Job records before prune_tasks
# deletes them.  Defaults to JOB_COMPLETED_RETENTION when not set.
JOB_FAILED_RETENTION = ENV.int("JOB_FAILED_RETENTION", default=90)


EXEMPT_VIEW_PERMISSIONS = []
CHANGELOG_SKIP_EMPTY_CHANGES = True
PAGINATE_COUNT = ENV.int("PAGINATE_COUNT", default=50)
MAX_PAGE_SIZE = ENV.int("MAX_PAGE_SIZE", default=1000)
DEFAULT_RESEARCH_WORK_PROVIDER_SEARCH_LIMIT = ENV.int("DEFAULT_RESEARCH_WORK_PROVIDER_SEARCH_LIMIT", default=50)
FILTERS_NULL_CHOICE_LABEL = "None"
FILTERS_NULL_CHOICE_VALUE = "null"
ALLOCATION_EXTENSION_REQUESTABLE_FIELDS = ENV.dict(
    "ALLOCATION_EXTENSION_REQUESTABLE_FIELDS",
    cast={"value": tuple},
    default={},
)
FIELD_CHOICES = ENV.dict("FIELD_CHOICES", cast={"value": parse_choices_from_env}, default={})
AUTO_SLUG_FUNC = ENV.str("AUTO_SLUG_FUNC", default="coldfront.models.utils.auto_generate_slug")
# ------------------------------------------------------------------------------
# System notifications
# ------------------------------------------------------------------------------
# Recipients for system notifications beyond superusers.
# Superusers always receive system notifications.
SYSTEM_NOTIFICATION_USERS = ENV.list("SYSTEM_NOTIFICATION_USERS", default=[])
SYSTEM_NOTIFICATION_GROUPS = ENV.list("SYSTEM_NOTIFICATION_GROUPS", default=[])

DEFAULT_USER_PREFERENCES = ENV.dict("DEFAULT_PERMISSIONS", default={})

DEFAULT_PERMISSIONS = ENV.dict(
    "DEFAULT_PERMISSIONS",
    default={
        # Permit users to manage their own API tokens
        "users.view_token": ({"user": "$user"},),
        "users.add_token": ({"user": "$user"},),
        "users.change_token": ({"user": "$user"},),
        "users.delete_token": ({"user": "$user"},),
        # Permit users to view all resources and resource types
        "ras.view_resource": ({"locked": False},),
        "slurm.view_slurmcluster": ({"locked": False},),
        "storage.view_storageresource": ({"locked": False},),
        "ras.view_resourcetype": None,
        # Permit users to view slurm partitions respecting any group/account restrictions
        "slurm.view_slurmpartition": (
            {
                "locked": False,
                "allow_groups": None,
                "allow_accounts": None,
            },
            {
                "locked": False,
                "allow_groups__user": "$user",
            },
            {
                "locked": False,
                "allow_accounts__associations__allocation__project__users__user": "$user",
                "allow_accounts__associations__allocation__status__in": ["active"],
            },
            {
                "locked": False,
                "allow_accounts__default_for_users__user": "$user",
            },
        ),
        # Permit users to view projects they own or are a member of
        "ras.view_project": (
            {"owner": "$user"},
            {"users__user": "$user"},
        ),
        # Permit users to view project users if they are the user, own the project or belong to same project
        "ras.view_projectuser": (
            {"user": "$user"},
            {"project__owner": "$user"},
            {"project__users__user": "$user"},
        ),
        # Permit users to view allocations they own, own the project, or are members of the project
        "ras.view_allocation": (
            {"owner": "$user"},
            {"project__owner": "$user"},
            {"project__users__user": "$user"},
        ),
        # Permit users to view slurm assocations for allocations they own or own the project
        "slurm.view_slurmassociation": (
            {"allocation__owner": "$user"},
            {"allocation__project__owner": "$user"},
            {"allocation__project__users__user": "$user"},
        ),
        # Permit users to view storage quotas for allocations they own or own the project
        "storage.view_storagequota": (
            {"allocation__owner": "$user"},
            {"allocation__project__owner": "$user"},
            {"allocation__project__users__user": "$user"},
        ),
        # Permit users to view publications linked to projects they own or are members of
        "ris.view_publication": (
            {"projects__owner": "$user"},
            {"projects__users__user": "$user"},
        ),
        # Permit users to view funding linked to projects they own or are members of
        "ris.view_funding": (
            {"projects__owner": "$user"},
            {"projects__users__user": "$user"},
        ),
    },
)

# Exclude potentially sensitive models from wildcard view exemption. These may still be exempted
# by specifying the model individually in the EXEMPT_VIEW_PERMISSIONS configuration parameter.
EXEMPT_EXCLUDE_MODELS = (
    ("users", "group"),
    ("users", "objectpermission"),
    ("users", "user"),
)

ALLOWED_URL_SCHEMES = [
    "file",
    "ftp",
    "ftps",
    "http",
    "https",
    "irc",
    "mailto",
    "sftp",
    "ssh",
    "tel",
    "telnet",
    "tftp",
    "vnc",
    "xmpp",
]

REST_FRAMEWORK_VERSION = coldfront.VERSION
REST_FRAMEWORK = {
    "ALLOWED_VERSIONS": [REST_FRAMEWORK_VERSION],
    "COERCE_DECIMAL_TO_STRING": False,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "coldfront.api.authentication.TokenAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_METADATA_CLASS": "coldfront.api.metadata.BulkOperationMetadata",
    "DEFAULT_PAGINATION_CLASS": "coldfront.api.paginator.OptionalLimitOffsetPagination",
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("coldfront.api.authentication.TokenPermissions",),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "coldfront.api.renderers.FormlessBrowsableAPIRenderer",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSION": REST_FRAMEWORK_VERSION,
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",
    "SCHEMA_COERCE_METHOD_NAMES": {
        # Default mappings
        "retrieve": "read",
        "destroy": "delete",
        # Custom operations
        #        'bulk_destroy': 'bulk_delete',
    },
    "VIEW_NAME_FUNCTION": "coldfront.api.utils.get_view_name",
}

#
# DRF Spectacular
#

SPECTACULAR_SETTINGS = {
    "TITLE": "ColdFront REST API",
    "LICENSE": {"name": "Apache 2.0"},
    "VERSION": coldfront.VERSION,
    "COMPONENT_SPLIT_REQUEST": True,
    "REDOC_DIST": "SIDECAR",
    "SERVERS": [
        {
            "url": "",
            "description": "ColdFront",
        }
    ],
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "POSTPROCESSING_HOOKS": [],
}

# Money
DEFAULT_CURRENCY = ENV.str("DEFAULT_CURRENCY", default="USD")
DEFAULT_CURRENCY_CHOICES = [
    x.split(":")
    for x in ENV.list(
        "DEFAULT_CURRENCY_CHOICES",
        default=[
            "USD:USD",
            "EUR:EUR",
            "JPY:JPY",
            "GBP:GBP",
            "CNY:CNY",
            "AUD:AUD",
            "CAD:CAD",
            "CHF:CHF",
            "HKD:HKD",
        ],
    )
]
CURRENCIES = [x[0] for x in DEFAULT_CURRENCY_CHOICES]
CURRENCY_CHOICES = DEFAULT_CURRENCY_CHOICES
