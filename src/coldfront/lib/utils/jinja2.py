# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from jinja2 import BaseLoader
from jinja2.sandbox import SandboxedEnvironment


def render_jinja2(template_code, context):
    """
    Render a Jinja2 template with the provided context.

    Args:
        template_code: The Jinja2 template string
        context: Dict of variables to pass to the template

    Returns:
        The rendered string
    """
    environment_params = {
        "loader": BaseLoader(),
    }
    environment = SandboxedEnvironment(**environment_params)
    template = environment.from_string(source=template_code)
    return template.render(**context)
