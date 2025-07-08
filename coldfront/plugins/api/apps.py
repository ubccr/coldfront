# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import os

from django.apps import AppConfig

from coldfront.core.utils.common import import_from_settings


class ApiConfig(AppConfig):
    name = "coldfront.plugins.api"

    def ready(self):
        # Dynamically add the api plugin templates directory to TEMPLATES['DIRS']
        BASE_DIR = import_from_settings("BASE_DIR")
        TEMPLATES = import_from_settings("TEMPLATES")
        api_templates_dir = os.path.join(BASE_DIR, "coldfront/plugins/api/templates")
        for template_setting in TEMPLATES:
            if api_templates_dir not in template_setting["DIRS"]:
                template_setting["DIRS"] = [api_templates_dir] + template_setting["DIRS"]
