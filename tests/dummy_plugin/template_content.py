# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.plugins.templates import PluginTemplateExtension


class GlobalContent(PluginTemplateExtension):
    def head(self):
        return "<!-- HEAD CONTENT -->"

    def navbar(self):
        return "GLOBAL CONTENT - NAVBAR"


class ProjectContent(PluginTemplateExtension):
    models = ["ras.project"]

    def buttons(self):
        return "PROJECT CONTENT - BUTTONS"

    def alerts(self):
        return "PROJECT CONTENT - ALERTS"

    def left_page(self):
        return "PROJECT CONTENT - LEFT PAGE"

    def right_page(self):
        return "PROJECT CONTENT - RIGHT PAGE"

    def full_width_page(self):
        return "PROJECT CONTENT - FULL WIDTH PAGE"

    def list_buttons(self):
        return "PROJECT CONTENT - LIST BUTTONS"


template_extensions = [GlobalContent, ProjectContent]
