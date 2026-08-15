# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

OBJECTCHANGE_FULL_NAME = """
{{ value.get_full_name|placeholder }}
"""

OBJECTCHANGE_OBJECT = """
{% if value and value.get_absolute_url %}
    <a href="{{ value.get_absolute_url }}">{{ record.object_repr }}</a>
{% else %}
    {{ record.object_repr }}
{% endif %}
"""

OBJECTCHANGE_REQUEST_ID = """
<a href="{% url 'core:objectchange_list' %}?request_id={{ value }}">{{ value }}</a>
"""

PLUGIN_IS_INSTALLED = """
{% if record.is_local %}
    {% if record.is_loaded %}
        <span class="text-success">{% cotton ui.checkmark :value="True" /%}</span>
    {% else %}
        <span class="text-danger"><i class="fa-solid fa-triangle-exclamation" data-bs-toggle="tooltip" title="Could not load plugin. Version may be incompa
tible. Min version: {{ record.coldfront_min_version }}, max version: {{ record.coldfront_max_version }}"></i></span>
    {% endif %}
{% else %}
    <span class="text-muted">&mdash;</span>
{% endif %}
"""

PLUGIN_NAME_TEMPLATE = """
{% load static %}
{% if record.icon_url %}
    <img class="plugin-icon" src="{{ record.icon_url }}">
{% else %}
    <span><i class="fa-solid fa-puzzle-piece"></i></span>
{% endif %}
<a href="{% url 'core:plugin' record.config_name %}">{{ record.title_long }}</a>
"""
