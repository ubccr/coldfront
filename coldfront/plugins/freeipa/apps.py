# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import importlib

from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings

FREEIPA_ENABLE_SIGNALS = import_from_settings("FREEIPA_ENABLE_SIGNALS", False)


class IPAConfig(AppConfig):
    name = "coldfront.plugins.freeipa"

    def ready(self):
        if FREEIPA_ENABLE_SIGNALS:
            importlib.import_module("coldfront.plugins.freeipa.signals")
