# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.apps import apps
from django.db.models import Q
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from coldfront.core.models import ObjectType
from coldfront.registry import registry


def get_table_configs(table, user):
    """
    Return any available TableConfigs applicable to the given table & user.
    """
    TableConfig = apps.get_model("core", "TableConfig")
    return TableConfig.objects.filter(
        Q(shared=True) | Q(user=user if user.is_authenticated else None),
        object_type=ObjectType.objects.get_for_model(table.Meta.model),
        table=table.name,
        enabled=True,
    )


def get_table_for_model(model, name=None):
    name = name or f"{model.__name__}Table"
    # Use the full app config path (e.g. "coldfront.ras") rather than the short
    # app_label (e.g. "ras") because Django apps are under the "coldfront" package.
    app_config = model._meta.app_config
    if app_config is not None:
        try:
            return import_string(f"{app_config.name}.tables.{name}")
        except ImportError:
            return None
    # Fall back to the app_label-only path for third-party apps
    try:
        return import_string(f"{model._meta.app_label}.tables.{name}")
    except ImportError:
        return None


def register_table_column(column, name, *tables):
    """
    Register a custom column for use on one or more tables.

    Args:
        column: The column instance to register
        name: The name of the table column
        tables: One or more table classes
    """
    for table in tables:
        reg = registry["tables"][table]
        if name in reg:
            raise ValueError(
                _("A column named {name} is already defined for table {table_name}").format(
                    name=name, table_name=table.__name__
                )
            )
        reg[name] = column
